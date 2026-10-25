import threading

from tests.conftest import create_event, rows

THREADS = 20
ROUNDS = 20


def race(app, event_id: int) -> list[int]:
    """THREADS clients POST distinct names at the same instant; returns their statuses."""
    barrier = threading.Barrier(THREADS)
    statuses: list[int] = []
    lock = threading.Lock()

    def attempt(n: int) -> None:
        racer = app.test_client()
        barrier.wait()
        resp = racer.post(f"/events/{event_id}/register", data={"name": f"racer{n}"})
        with lock:
            statuses.append(resp.status_code)

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return statuses


def test_last_seat_race_has_exactly_one_winner(app, client):
    for round_no in range(ROUNDS):
        event_id = create_event(client, capacity="5")
        for i in range(4):
            resp = client.post(f"/events/{event_id}/register", data={"name": f"seed{i}"})
            assert resp.status_code == 201

        statuses = race(app, event_id)

        assert sorted(statuses) == [201] + [409] * (THREADS - 1), f"round {round_no}: {statuses}"
        count = rows(app, "SELECT count(*) AS n FROM registrations WHERE event_id = ?", event_id)
        assert count[0]["n"] == 5, f"round {round_no}"
