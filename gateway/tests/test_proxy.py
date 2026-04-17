import respx
from httpx import Response


@respx.mock
def test_public_route_auth_passthrough(client):
    respx.post("http://auth.test/auth/login").mock(
        return_value=Response(200, json={"access_token": "tok", "user_id": 1})
    )
    r = client.post("/auth/login", json={"email": "a@b.c", "password": "x"})
    assert r.status_code == 200
    assert r.json()["access_token"] == "tok"


@respx.mock
def test_public_movies_list_no_auth_needed(client):
    respx.get("http://movie.test/movies").mock(return_value=Response(200, json=[]))
    r = client.get("/movies")
    assert r.status_code == 200


@respx.mock
def test_public_movie_detail(client):
    respx.get("http://movie.test/movies/1").mock(
        return_value=Response(200, json={"id": 1, "title": "Dune"})
    )
    r = client.get("/movies/1")
    assert r.status_code == 200
    assert r.json()["title"] == "Dune"


def test_protected_route_without_token(client):
    r = client.get("/bookings/1")
    assert r.status_code == 401


def test_protected_route_with_invalid_token(client):
    r = client.get("/bookings/1", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


@respx.mock
def test_protected_route_with_valid_token_injects_user_headers(client, valid_token):
    route = respx.get("http://booking.test/bookings/5").mock(
        return_value=Response(200, json={"id": 5})
    )
    r = client.get("/bookings/5", headers={"Authorization": f"Bearer {valid_token}"})
    assert r.status_code == 200

    assert route.called
    sent_headers = route.calls.last.request.headers
    assert sent_headers["x-user-id"] == "42"
    assert sent_headers["x-user-email"] == "alice@example.com"
    assert sent_headers["x-user-role"] == "customer"


def test_unknown_prefix_returns_404(client):
    r = client.get("/unknown/path")
    assert r.status_code == 404


@respx.mock
def test_payments_mock_page_is_public(client):
    respx.get("http://payment.test/payments/mock/3/page").mock(
        return_value=Response(200, text="<html>Pay</html>", headers={"content-type": "text/html"})
    )
    r = client.get("/payments/mock/3/page")
    assert r.status_code == 200
    assert "Pay" in r.text


def test_payments_other_requires_auth(client):
    r = client.get("/payments/1")
    assert r.status_code == 401


@respx.mock
def test_upstream_error_returns_502(client):
    import httpx
    respx.get("http://movie.test/movies/999").mock(side_effect=httpx.ConnectError("boom"))
    r = client.get("/movies/999")
    assert r.status_code == 502
