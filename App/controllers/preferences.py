from App.database import db
from App.controllers.user import get_user
from App.models import Preferences
from sqlalchemy.exc import IntegrityError


def _ensure_list(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _validate_unavailable_days(days):
    days = _ensure_list(days)
    if days is None:
        return None
    for d in days:
        if not isinstance(d, int) or d < 0 or d > 6:
            raise ValueError("unavailable_days must be integers in range 0..6")
    return days

def get_preferences(staff_id):
    """Return preferences JSON for a staff user or None if not found."""
    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise ValueError("Invalid staff member")

    prefs = Preferences.query.filter_by(staff_id=staff_id).first()
    if not prefs:
        return None
    return prefs.get_json()


def set_preferences(staff_id, *, preferred_shift_types=None, skills=None, unavailable_days=None, max_hours_per_week=None):
    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise ValueError("Invalid staff member")

    prefs = Preferences.query.filter_by(staff_id=staff_id).first()
    if not prefs:
        prefs = Preferences(staff_id=staff_id)

    # normalize and validate inputs
    if preferred_shift_types is not None:
        prefs.preferred_shift_types = _ensure_list(preferred_shift_types)
    if skills is not None:
        prefs.skills = _ensure_list(skills)
    if unavailable_days is not None:
        prefs.unavailable_days = _validate_unavailable_days(unavailable_days)
    if max_hours_per_week is not None:
        try:
            max_h = int(max_hours_per_week)
        except (TypeError, ValueError):
            raise ValueError("max_hours_per_week must be an integer")
        if max_h < 0 or max_h > 168:
            raise ValueError("max_hours_per_week must be between 0 and 168")
        prefs.max_hours_per_week = max_h

    db.session.add(prefs)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # If a race created the prefs row concurrently, try to re-query and return it
        existing = Preferences.query.filter_by(staff_id=staff_id).first()
        if existing:
            return existing
        raise

    return prefs
