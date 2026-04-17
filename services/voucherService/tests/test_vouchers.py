from datetime import datetime, timedelta


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_seed_vouchers_loaded(client):
    r = client.get("/vouchers")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    codes = {v["code"] for v in body}
    assert "WELCOME10" in codes
    assert "SUMMER50" in codes


def test_create_voucher_success(client):
    now = datetime.utcnow()
    r = client.post(
        "/vouchers",
        json={
            "code": "NEWYEAR25",
            "discount_percent": 25,
            "max_uses": 50,
            "valid_from": _iso(now - timedelta(days=1)),
            "valid_to": _iso(now + timedelta(days=30)),
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "NEWYEAR25"
    assert body["discount_percent"] == 25
    assert body["max_uses"] == 50
    assert body["used_count"] == 0


def test_create_voucher_duplicate_code(client):
    now = datetime.utcnow()
    payload = {
        "code": "DUPLICATE",
        "discount_percent": 15,
        "max_uses": 10,
        "valid_from": _iso(now - timedelta(days=1)),
        "valid_to": _iso(now + timedelta(days=10)),
    }
    r1 = client.post("/vouchers", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/vouchers", json=payload)
    assert r2.status_code == 409


def test_validate_valid_voucher(client):
    r = client.post(
        "/vouchers/validate",
        json={"code": "WELCOME10", "base_amount": 100.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["discount_amount"] == 10.0
    assert body["final_amount"] == 90.0


def test_validate_unknown_code(client):
    r = client.post(
        "/vouchers/validate",
        json={"code": "NOPE_NOT_REAL", "base_amount": 100.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False
    assert body["final_amount"] == 100.0


def test_validate_expired(client):
    now = datetime.utcnow()
    create = client.post(
        "/vouchers",
        json={
            "code": "EXPIRED1",
            "discount_percent": 20,
            "max_uses": 100,
            "valid_from": _iso(now - timedelta(days=10)),
            "valid_to": _iso(now - timedelta(days=1)),
        },
    )
    assert create.status_code == 201

    r = client.post(
        "/vouchers/validate",
        json={"code": "EXPIRED1", "base_amount": 200.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False


def test_validate_maxed_out(client):
    now = datetime.utcnow()
    create = client.post(
        "/vouchers",
        json={
            "code": "ONESHOT",
            "discount_percent": 30,
            "max_uses": 1,
            "valid_from": _iso(now - timedelta(days=1)),
            "valid_to": _iso(now + timedelta(days=10)),
        },
    )
    assert create.status_code == 201

    redeem = client.post("/vouchers/redeem", json={"code": "ONESHOT"})
    assert redeem.status_code == 200

    r = client.post(
        "/vouchers/validate",
        json={"code": "ONESHOT", "base_amount": 100.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is False


def test_redeem_increments_used_count(client):
    before = client.post(
        "/vouchers/validate",
        json={"code": "WELCOME10", "base_amount": 100.0},
    )
    assert before.status_code == 200

    r = client.post("/vouchers/redeem", json={"code": "WELCOME10"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == "WELCOME10"
    assert body["used_count"] == 1

    r2 = client.post("/vouchers/redeem", json={"code": "WELCOME10"})
    assert r2.status_code == 200
    assert r2.json()["used_count"] == 2


def test_redeem_unknown_code(client):
    r = client.post("/vouchers/redeem", json={"code": "NOPE_NOT_REAL"})
    assert r.status_code == 404
