from App.models import Shift
from App.database import db
from datetime import datetime
from App.controllers.user import get_user

def get_combined_roster(staff_id):
    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise PermissionError("Only staff can view roster")
    return [shift.get_json() for shift in Shift.query.order_by(Shift.start_time).all()]


def clock_in(staff_id, shift_id):
    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise PermissionError("Only staff can clock in")

    shift = db.session.get(Shift, shift_id)

    if not shift or shift.staff_id != staff_id:
        raise ValueError("Invalid shift for staff")
    if shift.clock_in is not None:
        raise ValueError("Shift already clocked in")

    shift.clock_in = datetime.now()
    db.session.commit()
    return shift


def clock_out(staff_id, shift_id):
    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise PermissionError("Only staff can clock out")

    shift = db.session.get(Shift, shift_id)
    if not shift or shift.staff_id != staff_id:
        raise ValueError("Invalid shift for staff")
    if shift.clock_out is not None:
        raise ValueError("Shift already clocked out")

    shift.clock_out = datetime.now()
    db.session.commit()
    return shift

def get_shift(shift_id):
    shift = db.session.get(Shift, shift_id)
    return shift