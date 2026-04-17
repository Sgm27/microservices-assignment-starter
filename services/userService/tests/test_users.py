def test_create_user_success(client):
    r = client.post(
        "/users",
        json={
            "email": "alice@example.com",
            "full_name": "Alice",
            "phone": "0900000001",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["full_name"] == "Alice"
    assert body["phone"] == "0900000001"
    assert body["id"] >= 1
    assert body["created_at"]

    got = client.get(f"/users/{body['id']}")
    assert got.status_code == 200
    assert got.json() == body


def test_create_user_with_explicit_id(client):
    r = client.post(
        "/users",
        json={
            "id": 42,
            "email": "bob@example.com",
            "full_name": "Bob",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 42
    assert body["email"] == "bob@example.com"

    got = client.get("/users/42")
    assert got.status_code == 200
    assert got.json()["id"] == 42


def test_create_user_duplicate_email(client):
    payload = {"email": "carol@example.com", "full_name": "Carol"}
    r1 = client.post("/users", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/users", json=payload)
    assert r2.status_code == 409


def test_create_user_duplicate_id(client):
    r1 = client.post(
        "/users",
        json={"id": 7, "email": "dan@example.com", "full_name": "Dan"},
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/users",
        json={"id": 7, "email": "dan2@example.com", "full_name": "Dan Two"},
    )
    assert r2.status_code == 409


def test_get_user_not_found(client):
    r = client.get("/users/9999")
    assert r.status_code == 404


def test_list_users(client):
    client.post(
        "/users",
        json={"email": "eve@example.com", "full_name": "Eve"},
    )
    client.post(
        "/users",
        json={"email": "frank@example.com", "full_name": "Frank"},
    )
    r = client.get("/users")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 2
    emails = {u["email"] for u in body}
    assert emails == {"eve@example.com", "frank@example.com"}
