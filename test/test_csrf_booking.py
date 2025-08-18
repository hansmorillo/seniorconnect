# test/test_csrf_booking.py
import re
import pytest
from datetime import date, timedelta
import importlib

@pytest.fixture
def app(monkeypatch):
    # 1) Point the config at SQLite *before* app.py imports it
    import config
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:")

    # 2) Import (or reload) app AFTER patching config so app.py reads the patched value
    import app as app_module
    importlib.reload(app_module)  # ensure it re-reads config constants
    a = app_module.create_app()

    # 3) Test-specific settings
    a.config.update(
        TESTING=True,
        WTF_CSRF_TIME_LIMIT=None,   # avoid expiry flakiness
        LOGIN_DISABLED=True,        # bypass @login_required during tests
    )

    # 4) Create tables on the test DB
    from extensions import db
    with a.app_context():
        db.create_all()
    return a

@pytest.fixture
def client(app):
    return app.test_client()

def _get_csrf_token_from_booking_page(html):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    assert m, "CSRF token not found in booking page"
    return m.group(1)

def _valid_booking_form_payload(token):
    tomorrow = (date.today().toordinal()+1)
    from datetime import date as _d
    d = _d.fromordinal(tomorrow).strftime("%Y-%m-%d")
    return {
        "csrf_token": token,
        "location": "Function Room",
        "date": d,
        "time": "8:00 AM – 9:00 AM",
        "eventTitle": "Yoga Demo",
        "interestGroup": "Yoga",
        "attendees": "10",
        "activityType": "Workshop",
        "equipment": "",
        "description": "",
        "organiserName": "Alice",
        "organiserEmail": "alice@example.com",
        "organiserPhone": "91234567",
        "accessibilityHelp": "No",
    }

def test_booking_rejects_without_csrf(client):
    # No GET (no token), direct POST => CSRFProtect should block
    r = client.post("/booking/success", data={"eventTitle": "x"})
    assert r.status_code in (302, 400)

def test_booking_rejects_with_invalid_csrf(client):
    client.get("/booking/")  # set up session
    bad = _valid_booking_form_payload("invalid-token")
    r = client.post("/booking/success", data=bad, follow_redirects=False)
    assert r.status_code in (302, 400)

def test_booking_accepts_with_valid_csrf_and_saves(client, app):
    r = client.get("/booking/")
    assert r.status_code == 200
    token = _get_csrf_token_from_booking_page(r.get_data(as_text=True))

    good = _valid_booking_form_payload(token)
    r2 = client.post("/booking/success", data=good, follow_redirects=True)
    assert r2.status_code == 200
    assert "Your booking has been successfully confirmed!" in r2.get_data(as_text=True)

    # verify DB row
    from extensions import db
    from models.booking import Booking
    with app.app_context():
        b = db.session.query(Booking).first()
        assert b is not None
        assert b.location == "Function Room"
        assert b.event_title == "Yoga Demo"
