def _first_showtime_id(client) -> int:
    movies = client.get("/movies").json()
    detail = client.get(f"/movies/{movies[0]['id']}").json()
    return detail["showtimes"][0]["id"]


def _status_map(client, showtime_id: int) -> dict[str, str]:
    seats = client.get(f"/showtimes/{showtime_id}/seats").json()
    return {s["seat_number"]: s["status"] for s in seats}


def test_reserve_seats_success(client):
    showtime_id = _first_showtime_id(client)

    r = client.post(
        "/seats/reserve",
        json={
            "showtime_id": showtime_id,
            "seat_numbers": ["A1", "A2"],
            "booking_id": 1001,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["booking_id"] == 1001

    statuses = _status_map(client, showtime_id)
    assert statuses["A1"] == "PENDING"
    assert statuses["A2"] == "PENDING"
    assert statuses["A3"] == "AVAILABLE"


def test_reserve_seats_conflict(client):
    showtime_id = _first_showtime_id(client)

    ok = client.post(
        "/seats/reserve",
        json={"showtime_id": showtime_id, "seat_numbers": ["A1"], "booking_id": 2001},
    )
    assert ok.status_code == 200

    conflict = client.post(
        "/seats/reserve",
        json={"showtime_id": showtime_id, "seat_numbers": ["A1"], "booking_id": 2002},
    )
    assert conflict.status_code == 409

    # Original PENDING state is unchanged.
    statuses = _status_map(client, showtime_id)
    assert statuses["A1"] == "PENDING"


def test_confirm_seats(client):
    showtime_id = _first_showtime_id(client)
    booking_id = 3001

    r = client.post(
        "/seats/reserve",
        json={
            "showtime_id": showtime_id,
            "seat_numbers": ["B1", "B2"],
            "booking_id": booking_id,
        },
    )
    assert r.status_code == 200

    conf = client.post("/seats/confirm", json={"booking_id": booking_id})
    assert conf.status_code == 200
    body = conf.json()
    assert body["status"] == "BOOKED"
    assert body["confirmed"] == 2

    statuses = _status_map(client, showtime_id)
    assert statuses["B1"] == "BOOKED"
    assert statuses["B2"] == "BOOKED"


def test_release_seats(client):
    showtime_id = _first_showtime_id(client)
    booking_id = 4001

    r = client.post(
        "/seats/reserve",
        json={
            "showtime_id": showtime_id,
            "seat_numbers": ["C1", "C2"],
            "booking_id": booking_id,
        },
    )
    assert r.status_code == 200

    rel = client.post("/seats/release", json={"booking_id": booking_id})
    assert rel.status_code == 200
    body = rel.json()
    assert body["status"] == "AVAILABLE"
    assert body["released"] == 2

    statuses = _status_map(client, showtime_id)
    assert statuses["C1"] == "AVAILABLE"
    assert statuses["C2"] == "AVAILABLE"


def test_release_idempotent(client):
    r = client.post("/seats/release", json={"booking_id": 999999})
    assert r.status_code == 200
    body = r.json()
    assert body["released"] == 0
    assert body["status"] == "AVAILABLE"
