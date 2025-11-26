from App.database import db
from App.models import User, Staff, Admin, Schedule, Shift, ShiftType
from datetime import datetime

# =========================================================
# RBAC and Helper Functions
# =========================================================

def _check_permissions(user_id, required_role):
    """Checks if a user has the required role to perform an action."""
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found.")
    
    # NOTE: This assumes User model has a 'role' property (e.g., 'admin', 'staff').
    # We check the role here to enforce your PermissionError tests.
    if user.role != required_role:
        raise PermissionError(f"Access Denied: User must be a '{required_role}'.")
    
    return user

def _get_shift_type_id_by_name(name):
    """Finds the ShiftType ID needed for the Shift Foreign Key."""
    type_obj = ShiftType.query.filter_by(name=name).first()
    if not type_obj:
        # Crucial error if you haven't run your initialization script!
        raise ValueError(f"Shift Type '{name}' not found. Please ensure types are seeded in the DB.")
    return type_obj.id

def get_shift(shift_id):
    """Basic retrieval helper."""
    return Shift.query.get(shift_id)

# =========================================================
# 1. Schedule Shift (Admin Action - UML: Admin.scheduleShift())
# =========================================================

def schedule_shift(admin_id, staff_id, schedule_id, start_time, end_time, shift_type_name="Morning"):
    """Creates a new Shift and assigns it to a Staff member within a Schedule."""
    
    # 1. PERMISSION CHECK (Ensures only Admin can create shifts)
    _check_permissions(admin_id, 'admin') 

    # 2. VALIDATION & FK LOOKUP
    staff = Staff.query.get(staff_id)
    schedule = Schedule.query.get(schedule_id)
    
    if not staff: raise ValueError(f"Staff with ID {staff_id} not found.")
    if not schedule: raise ValueError(f"Schedule with ID {schedule_id} not found.")
    if end_time <= start_time: raise ValueError("End time must be after start time.")

    # Get the required ShiftType ID
    type_id = _get_shift_type_id_by_name(shift_type_name)

    # 3. CREATION
    new_shift = Shift(
        staff_id=staff_id,
        schedule_id=schedule_id,
        shift_type_id=type_id,
        start_time=start_time,
        end_time=end_time
    )

    db.session.add(new_shift)
    db.session.commit()
    return new_shift

# =========================================================
# 2. Clock In (Staff Action - UML: Staff.clockIn())
# =========================================================

def clock_in(staff_id, shift_id):
    """Records the clock_in timestamp for a specific assigned shift."""
    
    # 1. PERMISSION CHECK (Ensures only Staff can use the time clock)
    _check_permissions(staff_id, 'staff') 
    
    shift = get_shift(shift_id)
    if not shift: raise ValueError("Shift not found.")
    if shift.staff_id != staff_id: raise PermissionError("Cannot clock into another staff member's shift.")
    if shift.clock_in is not None: raise ValueError("Already clocked in.")
    
    # Records the current time
    shift.clock_in = datetime.now() 
    db.session.commit()
    return shift

# =========================================================
# 3. Clock Out (Staff Action - UML: Staff.clockOut())
# =========================================================

def clock_out(staff_id, shift_id):
    """Records the clock_out timestamp for a specific assigned shift."""
    _check_permissions(staff_id, 'staff') 

    shift = get_shift(shift_id)
    if not shift: raise ValueError("Shift not found.")
    if shift.staff_id != staff_id: raise PermissionError("Cannot clock out from another staff member's shift.")
    if shift.clock_in is None: raise ValueError("Must clock in before clocking out.")
    if shift.clock_out is not None: raise ValueError("Already clocked out.")
    
    # Records the current time
    shift.clock_out = datetime.now() 
    db.session.commit()
    return shift

# =========================================================
# 4. Get Roster (Staff Action - UML: Staff.viewRoster())
# =========================================================

def get_combined_roster(staff_id):
    """Returns all shifts belonging to the schedules the staff member is part of."""
    
    # 1. PERMISSION CHECK 
    _check_permissions(staff_id, 'staff') 

    # Find all unique Schedule IDs this staff member is assigned to
    staff_schedules = db.session.query(Schedule.id).join(Shift).filter(Shift.staff_id == staff_id).distinct().all()
    schedule_ids = [s[0] for s in staff_schedules]

    # Find ALL shifts belonging to those schedules (The 'combined' view)
    all_shifts = Shift.query.filter(Shift.schedule_id.in_(schedule_ids)).all()
    
    return [shift.get_json() for shift in all_shifts]


# =========================================================
# 5. Get Report (Admin Action)
# =========================================================

def get_shift_report(admin_id):
    """Generates a report of all shifts for administrative review."""
    
    # 1. PERMISSION CHECK (Ensures only Admin can view system-wide reports)
    _check_permissions(admin_id, 'admin') 

    all_shifts = Shift.query.all()
    
    report = []
    for shift in all_shifts:
        data = shift.get_json()
        
        # Add staff username for the report view/test assertion
        staff_user = User.query.get(shift.staff_id)
        data["staff_name"] = staff_user.username if staff_user else "N/A"
        
        report.append(data)
        
    return report