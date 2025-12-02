from App.database import db
from App.models import User, Staff, Admin, Schedule, Shift
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound

# Import the permission checker helper from your shift controller
# NOTE: Make sure this function is importable (e.g., exposed in an __init__.py or the same file)
# from .shift_controllers import _check_permissions 

def _check_permissions(user_id, required_role):
    """Placeholder for the imported permission checker."""
    user = User.query.get(user_id)
    if not user: raise ValueError("User not found.")
    if user.role != required_role: raise PermissionError(f"Access Denied: User must be a '{required_role}'.")
    return user


def create_schedule(admin_id, name):
    """
    Creates a new schedule object, typically done by an Admin.
    """
    # 1. PERMISSION CHECK: Only Admins can create official schedules
    _check_permissions(admin_id, 'admin')

    # 2. VALIDATION: Check for unique name (optional but recommended)
    if Schedule.query.filter_by(name=name).first():
        raise ValueError(f"Schedule named '{name}' already exists.")

    # 3. CREATION
    new_schedule = Schedule(
        name=name,
        created_by=admin_id,
        # Note: We use created_by (User FK) and admin_id (Admin FK) as defined in your model
        admin_id=admin_id
    )
    
    db.session.add(new_schedule)
    db.session.commit()
    return new_schedule


def get_schedule(schedule_id):
    """
    Retrieves a single schedule by its ID.
    """
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        raise NoResultFound(f"Schedule with ID {schedule_id} not found.")
    return schedule

def get_all_schedules(admin_id):
    """
    Retrieves a list of all schedules in the system (Admin view).
    """
    # 1. PERMISSION CHECK: Viewing all schedules is usually restricted to Admins
    _check_permissions(admin_id, 'admin')
    
    schedules = Schedule.query.all()
    return [s.get_json() for s in schedules]

def update_schedule_name(admin_id, schedule_id, new_name):
    """
    Updates the name of an existing schedule.
    """
    # 1. PERMISSION CHECK
    _check_permissions(admin_id, 'admin')

    # 2. RETRIEVAL & VALIDATION
    schedule = get_schedule(schedule_id)
    if Schedule.query.filter_by(name=new_name).first():
        raise ValueError(f"Schedule named '{new_name}' already exists.")

    # 3. UPDATE
    schedule.name = new_name
    db.session.commit()
    return schedule

def delete_schedule(admin_id, schedule_id):
    """
    Deletes a schedule and all associated shifts (due to cascade).
    """
    # 1. PERMISSION CHECK
    _check_permissions(admin_id, 'admin')
    
    schedule = get_schedule(schedule_id)

    # 2. DELETION
    db.session.delete(schedule)
    db.session.commit()
    
    # Check that all associated shifts were deleted (for confidence/testing)
    if Shift.query.filter_by(schedule_id=schedule_id).count() == 0:
        return {"message": f"Schedule '{schedule.name}' and its {len(schedule.shifts)} shifts successfully deleted."}
    else:
        # This should theoretically not happen if cascade is working
        return {"error": "Schedule deleted, but shifts remain. Check model configuration."}
