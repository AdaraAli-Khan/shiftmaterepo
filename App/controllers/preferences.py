from App.database import db
from App.controllers.user import get_user
from App.models import Preferences

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

    if preferred_shift_types is not None:
        prefs.preferred_shift_types = preferred_shift_types
    if skills is not None:
        prefs.skills = skills
    if unavailable_days is not None:
        prefs.unavailable_days = unavailable_days
    if max_hours_per_week is not None:
        prefs.max_hours_per_week = max_hours_per_week

    db.session.add(prefs)
    db.session.commit()
    return prefs
