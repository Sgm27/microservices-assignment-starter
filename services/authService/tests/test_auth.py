def test_register_success(client):
    r = client.post(
        "/auth/register",
        json={
            "email": "alice@example.com",
            "password": "secret123",
            "full_name": "Alice",
            "phone": "0900000001",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "customer"
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user_id"] >= 1


def test_register_duplicate_email(client):
    payload = {
        "email": "bob@example.com",
        "password": "secret123",
        "full_name": "Bob",
    }
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409


def test_login_success_and_invalid(client):
    client.post(
        "/auth/register",
        json={"email": "carol@example.com", "password": "secret123", "full_name": "Carol"},
    )
    ok = client.post("/auth/login", json={"email": "carol@example.com", "password": "secret123"})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = client.post("/auth/login", json={"email": "carol@example.com", "password": "wrong"})
    assert bad.status_code == 401

    missing = client.post("/auth/login", json={"email": "nope@example.com", "password": "x"})
    assert missing.status_code == 401


def test_verify_round_trip(client):
    reg = client.post(
        "/auth/register",
        json={"email": "dan@example.com", "password": "secret123", "full_name": "Dan"},
    )
    token = reg.json()["access_token"]

    ok = client.post("/auth/verify", json={"token": token})
    assert ok.status_code == 200
    body = ok.json()
    assert body["valid"] is True
    assert body["email"] == "dan@example.com"
    assert body["role"] == "customer"

    bad = client.post("/auth/verify", json={"token": "not-a-jwt"})
    assert bad.status_code == 401
