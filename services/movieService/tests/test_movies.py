def test_seed_movies_present(client):
    r = client.get("/movies")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 3
    assert {m["title"] for m in body} >= {"Dune: Part Two", "Inside Out 2", "The Batman"}


def test_get_movie_detail_with_showtimes(client):
    movies = client.get("/movies").json()
    movie_id = movies[0]["id"]

    r = client.get(f"/movies/{movie_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == movie_id
    assert body["title"] == movies[0]["title"]
    assert "showtimes" in body
    assert len(body["showtimes"]) == 2
    first = body["showtimes"][0]
    assert set(first.keys()) >= {"id", "room", "starts_at", "base_price"}


def test_get_movie_not_found(client):
    r = client.get("/movies/999999")
    assert r.status_code == 404


def test_get_showtime_with_seats_count(client):
    movies = client.get("/movies").json()
    movie_id = movies[0]["id"]
    detail = client.get(f"/movies/{movie_id}").json()
    showtime_id = detail["showtimes"][0]["id"]

    st = client.get(f"/showtimes/{showtime_id}")
    assert st.status_code == 200
    st_body = st.json()
    assert st_body["id"] == showtime_id
    assert st_body["movie"]["id"] == movie_id

    seats = client.get(f"/showtimes/{showtime_id}/seats")
    assert seats.status_code == 200
    seat_list = seats.json()
    assert len(seat_list) == 30
    assert all(s["status"] == "AVAILABLE" for s in seat_list)
