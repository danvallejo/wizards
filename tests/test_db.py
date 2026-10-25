from app.db import get_db


def test_one_connection_per_request(app):
    with app.app_context():
        assert get_db() is get_db()
