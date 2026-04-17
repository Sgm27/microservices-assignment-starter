def _payload(email: str = "alice@example.com", subject: str = "Hello", body: str = "World"):
    return {
        "user_id": 1,
        "email": email,
        "subject": subject,
        "body": body,
    }


def test_send_notification_mock_succeeds(client):
    r = client.post("/notifications/send", json=_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SENT"
    assert body["sent_at"] is not None
    assert body["error"] is None
    assert body["email"] == "alice@example.com"
    assert body["subject"] == "Hello"
    assert body["body"] == "World"
    assert body["user_id"] == 1
    assert body["id"] >= 1


def test_list_notifications(client):
    first = client.post(
        "/notifications/send", json=_payload(subject="First", body="one")
    )
    assert first.status_code == 201
    second = client.post(
        "/notifications/send", json=_payload(subject="Second", body="two")
    )
    assert second.status_code == 201

    r = client.get("/notifications")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2
    # most recent first
    assert items[0]["id"] >= items[1]["id"]
    assert items[0]["subject"] == "Second"
    assert items[1]["subject"] == "First"


def test_get_notification_by_id(client):
    created = client.post("/notifications/send", json=_payload(subject="Look up"))
    assert created.status_code == 201
    nid = created.json()["id"]

    r = client.get(f"/notifications/{nid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == nid
    assert body["subject"] == "Look up"
    assert body["status"] == "SENT"


def test_get_notification_not_found(client):
    r = client.get("/notifications/99999")
    assert r.status_code == 404


def test_send_notification_validation_error(client):
    r = client.post("/notifications/send", json={"user_id": 1})
    assert r.status_code == 422
