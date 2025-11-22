from datetime import datetime, date, time, timedelta

from App.models import Shift, Schedule
from App.database import db
from App.controllers.user import get_user


def _ensure_admin(admin_id):
    # allow None to fall through to normal admin check
    try:
        admin_id = int(admin_id)
    except (TypeError, ValueError):
        raise PermissionError("Only admins can view shift reports")

    admin = get_user(admin_id)
    if not admin or admin.role != "admin":
        raise PermissionError("Only admins can view shift reports")

    return admin


def create_schedule(admin_id, scheduleName):
    """
    UML: Admin.scheduleShift() – creating a Schedule object.
    Called by /createSchedule in AdminViews.py
    """
    _ensure_admin(admin_id)

    if not scheduleName or not scheduleName.strip():
        raise ValueError("Schedule name is required")

    new_schedule = Schedule(
        created_by=int(admin_id),
        name=scheduleName.strip(),
        created_at=datetime.utcnow()
    )

    db.session.add(new_schedule)
    db.session.commit()

    return new_schedule


def schedule_shift(admin_id, staff_id, schedule_id, start_time, end_time):
    """
    UML: Admin.scheduleShift() – assign a shift to a staff member.
    Called by /createShift in AdminViews.py
    """
    _ensure_admin(admin_id)

    # Cast IDs safely; JWT identity is a string
    try:
        staff_id = int(staff_id)
        schedule_id = int(schedule_id)
    except (TypeError, ValueError):
        raise ValueError("Invalid staff or schedule id")

    staff = get_user(staff_id)
    if not staff or staff.role != "staff":
        raise ValueError("Invalid staff member")

    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        raise ValueError("Invalid schedule ID")

    if start_time >= end_time:
        raise ValueError("Shift start time must be before end time")

    new_shift = Shift(
        staff_id=staff_id,
        schedule_id=schedule_id,
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(new_shift)
    db.session.commit()

    return new_shift


def get_shift_report(admin_id):
    """
    UML: Admin.viewShift() – get a list of all shifts (report).
    Called by /shiftReport in AdminViews.py
    """
    _ensure_admin(admin_id)

    # For now: simple report (can be grouped by staff/schedule later)
    shifts = Shift.query.order_by(Shift.start_time).all()
    return [shift.get_json() for shift in shifts]

def auto_populate(
    admin_id,
    strategy_name,
    staff_list,
    start_date,
    end_date,
    shifts_per_day: int = 1,
    shift_length_hours: int = 8,
):
    """
    UML: Admin.auto_populate(strategy, staff_list, start_date, end_date, shift_per_day)

    Creates a Schedule and automatically generates Shift rows for the given
    staff_list between start_date and end_date, using a simple round-robin
    assignment.

    Raises:
        PermissionError: if admin_id is not an admin (via _ensure_admin)
        ValueError: if staff_list is empty, dates invalid, or shifts_per_day <= 0
    """
    _ensure_admin(admin_id)  # will raise PermissionError with your message

    if not staff_list:
        raise ValueError("Staff list cannot be empty")

    # normalise dates (accept date or datetime)
    def to_date(d):
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
        raise TypeError("start_date and end_date must be date or datetime")

    start = to_date(start_date)
    end = to_date(end_date)

    if start > end:
        raise ValueError("start_date must be on or before end_date")

    if shifts_per_day <= 0:
        raise ValueError("shifts_per_day must be positive")

    schedule_name = f"Auto {strategy_name or 'schedule'} {start}–{end}"
    schedule = Schedule(
        name=schedule_name,
        created_by=int(admin_id),
        created_at=datetime.utcnow(),
    )
    db.session.add(schedule)
    db.session.flush()  # get schedule.id before commit

    total_days = (end - start).days + 1
    num_staff = len(staff_list)

    for day_index in range(total_days):
        day = start + timedelta(days=day_index)

        for shift_index in range(shifts_per_day):
            staff = staff_list[(day_index * shifts_per_day + shift_index) % num_staff]

            # e.g. 08:00, 16:00 etc. depending on shift_length_hours
            shift_start = datetime.combine(day, time(8, 0)) + timedelta(
                hours=shift_index * shift_length_hours
            )
            shift_end = shift_start + timedelta(hours=shift_length_hours)

            new_shift = Shift(
                staff_id=staff.id,
                schedule_id=schedule.id,
                start_time=shift_start,
                end_time=shift_end,
            )
            db.session.add(new_shift)

    db.session.commit()
    return schedule