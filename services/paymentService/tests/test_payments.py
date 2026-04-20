def _create(client, booking_id=101, amount="150000.00"):
    return client.post(
        "/payments/create",
        json={"booking_id": booking_id, "amount": amount},
    )


def test_create_payment_returns_url(client):
    r = _create(client, booking_id=101, amount="150000.00")
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["payment_id"] >= 1
    assert body["payment_url"].endswith(f"/payments/{body['payment_id']}/checkout")


def test_create_payment_duplicate_booking_id(client):
    r1 = _create(client, booking_id=202, amount="99000.00")
    assert r1.status_code == 201

    r2 = _create(client, booking_id=202, amount="99000.00")
    assert r2.status_code == 409


def test_get_payment_by_id(client):
    created = _create(client, booking_id=303, amount="75000.00").json()

    r = client.get(f"/payments/{created['payment_id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["payment_id"]
    assert body["booking_id"] == 303
    assert body["status"] == "PENDING"
    assert body["provider"] == "vnpay"


def test_get_payment_by_booking_id(client):
    created = _create(client, booking_id=404, amount="50000.00").json()

    r = client.get("/payments/by-booking/404")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["payment_id"]
    assert body["booking_id"] == 404


def test_get_payment_not_found(client):
    r = client.get("/payments/99999")
    assert r.status_code == 404

    r2 = client.get("/payments/by-booking/99999")
    assert r2.status_code == 404


def test_confirm_payment_success(client):
    created = _create(client, booking_id=505, amount="120000.00").json()

    r = client.post(
        f"/payments/{created['payment_id']}/confirm",
        json={"success": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "SUCCESS"
    assert body["provider_txn_id"] == f"vnpay-{created['payment_id']}"


def test_confirm_payment_failure(client):
    created = _create(client, booking_id=606, amount="60000.00").json()

    r = client.post(
        f"/payments/{created['payment_id']}/confirm",
        json={"success": False},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "FAILED"


def test_confirm_payment_already_finalized(client):
    created = _create(client, booking_id=707, amount="80000.00").json()

    first = client.post(
        f"/payments/{created['payment_id']}/confirm",
        json={"success": True},
    )
    assert first.status_code == 200

    second = client.post(
        f"/payments/{created['payment_id']}/confirm",
        json={"success": True},
    )
    assert second.status_code == 400


def test_checkout_page_renders(client):
    created = _create(client, booking_id=808, amount="40000.00").json()

    r = client.get(f"/payments/{created['payment_id']}/checkout")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "VNPay" in r.text


def test_cancel_pending_payment(client):
    created = _create(client, booking_id=1001, amount="100000.00").json()

    r = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["payment_id"]
    assert body["status"] == "CANCELLED"


def test_cancel_idempotent_when_already_cancelled(client):
    created = _create(client, booking_id=1002, amount="100000.00").json()

    first = client.post(f"/payments/{created['payment_id']}/cancel")
    assert first.status_code == 200

    second = client.post(f"/payments/{created['payment_id']}/cancel")
    assert second.status_code == 200
    assert second.json()["status"] == "CANCELLED"


def test_cancel_failed_payment(client):
    created = _create(client, booking_id=1003, amount="100000.00").json()

    r1 = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": False})
    assert r1.status_code == 200
    assert r1.json()["status"] == "FAILED"

    r2 = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r2.status_code == 200
    assert r2.json()["status"] == "CANCELLED"


def test_cancel_success_rejected(client):
    created = _create(client, booking_id=1004, amount="100000.00").json()

    r1 = client.post(f"/payments/{created['payment_id']}/confirm", json={"success": True})
    assert r1.status_code == 200

    r2 = client.post(f"/payments/{created['payment_id']}/cancel")
    assert r2.status_code == 409


def test_cancel_not_found(client):
    r = client.post("/payments/99999/cancel")
    assert r.status_code == 404
