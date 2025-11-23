import pytest
from App.main import create_app
from App.controllers import create_user
from App.controllers.preferences import set_preferences, get_preferences
from App.database import db, create_db


@pytest.fixture(autouse=True)
def clean_db_local():
    # run these unit tests inside an application context with an in-memory sqlite DB
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    ctx = app.app_context()
    ctx.push()
    try:
        db.drop_all()
        create_db()
        yield
    finally:
        db.session.remove()
        db.drop_all()
        ctx.pop()


def test_set_and_get_preferences_unit():
    # create a staff user
    staff = create_user("pref_staff", "pass", "staff")

    # set preferences
    prefs = set_preferences(
        staff.id,
        preferred_shift_types=["morning", "evening"],
        skills=["cashier", "stocking"],
        unavailable_days=[6],
        max_hours_per_week=30,
    )

    assert prefs.staff_id == staff.id
    got = get_preferences(staff.id)
    assert got is not None
    assert got["preferred_shift_types"] == ["morning", "evening"]
    assert got["skills"] == ["cashier", "stocking"]
    assert got["unavailable_days"] == [6]
    assert got["max_hours_per_week"] == 30


def test_setting_preferences_invalid_user():
    # non-existent user id should raise
    with pytest.raises(ValueError):
        set_preferences(999, preferred_shift_types=["morning"]) 
