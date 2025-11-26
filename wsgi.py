import click, pytest, sys, os
from flask.cli import with_appcontext, AppGroup
from datetime import datetime
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from App.database import db, get_migrate
from App.models import User
from App.main import create_app 
from App.controllers import (
    create_user, get_all_users_json, get_all_users, initialize,
    schedule_shift, get_combined_roster, clock_in, clock_out, get_shift_report, login,loginCLI
)
from App.controllers import set_preferences, get_preferences

app = create_app()
migrate = get_migrate(app)

def _print_banner():
    try:
        banner_path = 'App/banner.txt'
        if os.path.exists(banner_path):
            with open(banner_path, 'r', encoding='utf-8') as f:
                banner_content = f.read()
                print("\n" + banner_content)
        else:
            print("\n" + "=" * 60)
            print("                    S H I F T M A T E")
            print("=" * 60)
    except Exception as e:
        print("\n" + "=" * 60)
        print("SHIFTMATE ROSTERING SYSTEM")
        print("=" * 60)

def _print_table(headers, rows):
    if not rows:
        print("No data available")
        return
    
    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(str(header))
        for row in rows:
            if i < len(row):
                max_width = max(max_width, len(str(row[i])))
        col_widths.append(max_width + 2)  
    
    # Print header
    separator_line = "+"
    header_line = "|"
    for i, width in enumerate(col_widths):
        separator_line += f"{'-' * (width)}+"
        if i < len(headers):
            header_line += f" {headers[i]:<{width-1}}|"
    
    print(separator_line)
    print(header_line)
    print(separator_line)
    
    # Print data rows
    for row in rows:
        row_line = "|"
        for i, cell in enumerate(row):
            if i < len(row):
                row_line += f" {str(cell):<{col_widths[i]-1}}|"
        print(row_line)
    
    print(separator_line)

def _print_clock_message(action, datetime_obj, username):
    print(f"\n{action}")
    print("=" * 40)
    print(f"You have been {action.lower()} at")
    print(f"Date: {datetime_obj.strftime('%m/%d/%Y')}")
    print(f"Time: {datetime_obj.strftime('%I:%M %p')}")
    print("=" * 40)

@app.cli.command("init", help="Creates and initializes the database")
def init():
    _print_banner()
    initialize()
    print('database initialized')

auth_cli = AppGroup('auth', help='Authentication commands')

@auth_cli.command("login", help="Login and get JWT token")
@click.argument("username")
@click.argument("password")
def login_command(username, password):
    _print_banner()
    
    result = loginCLI(username, password)
    if result["message"] in ["Login successful", "User already logged in"]:
        token = result["token"]
        with open("active_token.txt", "w") as f:
            f.write(token)
        print(f"✅ {result['message']}! JWT token saved for CLI use.")
    else:
        print(f"⚠️ {result['message']}")

@auth_cli.command("whoami", help="Check current logged in user")
def whoami_command():
    _print_banner()
    
    import os
    from flask_jwt_extended import decode_token
    from App.controllers import get_user

    if not os.path.exists("active_token.txt"):
        print("⚠️ No active session. Please login first.")
        return

    try:
        with open("active_token.txt", "r") as f:
            token = f.read().strip()

        decoded = decode_token(token)
        user_id = decoded["sub"]
        user = get_user(user_id)
        
        if user:
            headers = ["User ID", "Username", "Role"]
            rows = [[user.id, user.username, user.role]]
            print("🔐 Current User:")
            _print_table(headers, rows)
        else:
            print("❌ User not found")
            
    except Exception as e:
        print(f"❌ Invalid or expired token: {e}")

@auth_cli.command("logout", help="Logout current user")
def logout_command():
    _print_banner()
    
    if not os.path.exists("active_token.txt"):
        print("⚠️ No active session. Please login first.")
        return

    try:
        # Remove the token file to logout
        os.remove("active_token.txt")
        print("✅ Successfully logged out!")
    except Exception as e:
        print(f"❌ Error during logout: {e}")
    
app.cli.add_command(auth_cli)

user_cli = AppGroup('user', help='User object commands') 

@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
@click.argument("role", default="staff")
def create_user_command(username, password, role):
    _print_banner()
    create_user(username, password, role)
    print(f'{username} created!')

@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    _print_banner()
    if format == 'string':
        users = get_all_users()
        headers = ["ID", "Username", "Role"]
        rows = []
        for user in users:
            rows.append([user.id, user.username, user.role])
        print(f"👥 User List ({len(users)} users):")
        _print_table(headers, rows)
    else:
        print(get_all_users_json())

app.cli.add_command(user_cli)

shift_cli = AppGroup('shift', help='Shift management commands')

@shift_cli.command("schedule", help="Admin schedules a shift and assigns it to a schedule")
@click.argument("staff_id", type=int)
@click.argument("schedule_id", type=int)
@click.argument("start")
@click.argument("end")
def schedule_shift_command(staff_id, schedule_id, start, end):
    from datetime import datetime
    admin = require_admin_login()
    _print_banner()
    start_time = datetime.fromisoformat(start)
    end_time = datetime.fromisoformat(end)
    shift = schedule_shift(admin.id, staff_id, schedule_id, start_time, end_time)
    print(f"✅ Shift scheduled under Schedule {schedule_id} by {admin.username}:")
    if hasattr(shift, 'get_json'):
        print(shift.get_json())

@shift_cli.command("roster", help="Staff views combined roster")
def roster_command():
    staff = require_staff_login()
    _print_banner()
    
    from App.models import Shift
    # Get shifts assigned to this staff member
    shifts = Shift.query.filter_by(staff_id=staff.id).all()
    
    if shifts:
        headers = ["Shift ID", "Start Time", "End Time", "Status"]
        rows = []
        for shift in shifts:
            start_time = shift.start_time.strftime('%m/%d/%Y %I:%M %p') if shift.start_time else 'N/A'
            end_time = shift.end_time.strftime('%m/%d/%Y %I:%M %p') if shift.end_time else 'N/A'
            status = "Completed" if shift.clock_out else "In Progress" if shift.clock_in else "Scheduled"
            rows.append([shift.id, start_time, end_time, status])
        print(f"📋 Schedule View for {staff.username}:")
        _print_table(headers, rows)
    else:
        print("📋 No shifts scheduled for you.")

@shift_cli.command("clockin", help="Staff clocks in")
@click.argument("shift_id", type=int)
def clockin_command(shift_id):
    staff = require_staff_login()
    _print_banner()
    shift = clock_in(staff.id, shift_id)
    if shift and hasattr(shift, 'clock_in'):
        _print_clock_message("Clock In", shift.clock_in, staff.username)
    else:
        print("❌ Failed to clock in")

@shift_cli.command("clockout", help="Staff clocks out")
@click.argument("shift_id", type=int)
def clockout_command(shift_id):
    staff = require_staff_login()
    _print_banner()
    shift = clock_out(staff.id, shift_id)
    if shift and hasattr(shift, 'clock_out'):
        _print_clock_message("Clock Out", shift.clock_out, staff.username)
    else:
        print("❌ Failed to clock out")

@shift_cli.command("report", help="Admin views shift report")
def report_command():
    admin = require_admin_login()
    _print_banner()
    
    from App.models import Shift
    # Get all shifts across all schedules
    shifts = Shift.query.all()
    
    if shifts:
        headers = ["Shift ID", "Staff", "Start Time", "End Time", "Status"]
        rows = []
        for shift in shifts:
            staff_name = getattr(shift.staff, 'username', 'Unknown') if shift.staff else 'Unknown'
            start_time = shift.start_time.strftime('%m/%d/%Y %I:%M %p') if shift.start_time else 'N/A'
            end_time = shift.end_time.strftime('%m/%d/%Y %I:%M %p') if shift.end_time else 'N/A'
            status = "Completed" if shift.clock_out else "In Progress" if shift.clock_in else "Scheduled"
            rows.append([shift.id, staff_name, start_time, end_time, status])
        print(f"📊 Shift Report for {admin.username}:")
        _print_table(headers, rows)
    else:
        print("📊 No shifts found in the system.")

app.cli.add_command(shift_cli)

def require_admin_login():
    import os
    from flask_jwt_extended import decode_token
    from App.controllers import get_user

    if not os.path.exists("active_token.txt"):
        raise PermissionError("⚠️ No active session. Please login first.")

    with open("active_token.txt", "r") as f:
        token = f.read().strip()

    try:
        decoded = decode_token(token)
        user_id = decoded["sub"]
        user = get_user(user_id)
        if not user or user.role != "admin":
            raise PermissionError("🚫 Only an admin can use this command.")
        return user
    except Exception as e:
        raise PermissionError(f"Invalid or expired token. Please login again. ({e})")

def require_staff_login():
    import os
    from flask_jwt_extended import decode_token
    from App.controllers import get_user

    if not os.path.exists("active_token.txt"):
        raise PermissionError("⚠️ No active session. Please login first.")

    with open("active_token.txt", "r") as f:
        token = f.read().strip()

    try:
        decoded = decode_token(token)
        user_id = decoded["sub"]
        user = get_user(user_id)
        if not user or user.role != "staff":
            raise PermissionError("🚫 Only staff can use this command.")
        return user
    except Exception as e:
        raise PermissionError(f"Invalid or expired token. Please login again. ({e})")

schedule_cli = AppGroup('schedule', help='Schedule management commands')

@schedule_cli.command("create", help="Create a schedule")
@click.argument("name")
def create_schedule_command(name):
    from App.models import Schedule
    admin = require_admin_login()
    _print_banner()
    schedule = Schedule(name=name, created_by=admin.id)
    db.session.add(schedule)
    db.session.commit()
    
    # Print in table format instead of JSON
    headers = ["Field", "Value"]
    schedule_data = schedule.get_json()
    rows = [
        ["Schedule ID", schedule_data['id']],
        ["Name", schedule_data['name']],
        ["Created By", f"Admin ID: {schedule_data['created_by']}"],
        ["Created At", schedule_data['created_at']],
        ["Total Shifts", schedule_data['shift_count']]
    ]
    
    print("✅ Schedule Created Successfully:")
    _print_table(headers, rows)

@schedule_cli.command("list", help="List all schedules")
def list_schedules_command():
    from App.models import Schedule
    admin = require_admin_login()
    _print_banner()
    schedules = Schedule.query.all()
    
    headers = ["ID", "Name", "Created By", "Shifts"]
    rows = []
    for schedule in schedules:
        shift_count = len(schedule.shifts) if hasattr(schedule, 'shifts') else 0
        rows.append([schedule.id, schedule.name, schedule.created_by, shift_count])
    
    print(f"✅ Found {len(schedules)} schedule(s):")
    _print_table(headers, rows)

@schedule_cli.command("view", help="View a schedule and its shifts")
@click.argument("schedule_id", type=int)
def view_schedule_command(schedule_id):
    from App.models import Schedule
    admin = require_admin_login()
    _print_banner()
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        print("⚠️ Schedule not found.")
    else:
        print(f"✅ Viewing schedule {schedule_id}:")
        if hasattr(schedule, 'shifts') and schedule.shifts:
            headers = ["Shift ID", "Staff", "Start Time", "End Time", "Status"]
            rows = []
            for shift in schedule.shifts:
                staff_name = getattr(shift.staff, 'username', 'Unknown') if shift.staff else 'Unknown'
                start_time = shift.start_time.strftime('%m/%d/%Y %I:%M %p') if shift.start_time else 'N/A'
                end_time = shift.end_time.strftime('%m/%d/%Y %I:%M %p') if shift.end_time else 'N/A'
                status = "Completed" if shift.clock_out else "In Progress" if shift.clock_in else "Scheduled"
                rows.append([shift.id, staff_name, start_time, end_time, status])
            _print_table(headers, rows)
        else:
            print("No shifts in this schedule")

@schedule_cli.command("auto", help="Auto-generate schedule using AI strategies (SPECIAL FEATURE)")
@click.argument("schedule_id", type=int)
@click.argument("strategy", default="even-distribute")
@click.option("--days", default=7, help="Number of days to schedule")
@click.option("--shifts-per-day", default=2, help="Number of shifts per day")
@click.option("--shift-type", default="mixed", help="Shift types: day, night, or mixed")
def auto_schedule_command(schedule_id, strategy, days, shifts_per_day, shift_type):
    from App.controllers.scheduling.schedule_client import schedule_client
    from App.models import Staff, Schedule
    from datetime import datetime, timedelta
    
    admin = require_admin_login()
    _print_banner()
    
    # Verify schedule exists
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        print("❌ Schedule not found.")
        return
    
    # Get all available staff
    staff_list = Staff.query.all()
    if not staff_list:
        print("❌ No staff available. Create staff members first.")
        return
    
    # Set date range
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days)
    
    # Validate strategy
    available = schedule_client.get_available_strategies()
    if strategy not in available:
        print(f"❌ Invalid strategy. Available: {', '.join(available)}")
        return
    
    # Validate shift type
    if shift_type not in ['day', 'night', 'mixed']:
        print("❌ Invalid shift type. Use: day, night, or mixed")
        return
    
    try:
        print(f"\n🔄 Generating {strategy} schedule...")
        print(f"   📅 Schedule: {schedule.name} (ID: {schedule_id})")
        print(f"   📆 Period: {days} days, Shifts/day: {shifts_per_day}, Type: {shift_type}")
        print(f"   👥 Staff: {len(staff_list)} employees")
        
        result = schedule_client.auto_populate(
            admin_id=admin.id,
            schedule_id=schedule_id,
            strategy_name=strategy,
            staff_list=staff_list,
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=shifts_per_day,
            shift_type=shift_type
        )
        
        if result['success']:
            print(f"\n✅ Schedule auto-generated using '{strategy}' strategy!")
            print(f"📊 Performance Score: {result['score']:.1f}/100")
            print(f"👥 Shifts Created: {result['shifts_created']}")
            
            # Handle the summary display properly
            summary = result.get('summary', {})
            if isinstance(summary, str):
                # If summary is already a formatted string, just print it
                print(f"\n📈 Summary:\n{summary}")
            elif isinstance(summary, dict):
                # If summary is a dict, display it as a table
                headers = ["Metric", "Value"]
                rows = [
                    ["👥 Total Staff", summary.get('total_staff', 0)],
                    ["✅ Staff with Assignments", summary.get('staff_with_assignments', 0)],
                    ["⏰ Total Hours", f"{summary.get('total_hours_assigned', 0):.0f}h"],
                    ["📈 Average Hours/Staff", f"{summary.get('average_hours_per_staff', 0):.0f}h"],
                    ["📊 Hours Range", f"{summary.get('min_hours', 0):.0f}h - {summary.get('max_hours', 0):.0f}h"],
                    ["📅 Total Shifts", summary.get('total_shifts_assigned', 0)],
                    ["🔄 Shifts Range", f"{summary.get('min_shifts', 0)} - {summary.get('max_shifts', 0)}"],
                    ["⭐ Fairness Score", f"{summary.get('fairness_score', 0):.0f}/100"]
                ]
                print("\n📈 Schedule Summary:")
                _print_table(headers, rows)
            else:
                print(f"\n📈 Summary: {summary}")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Failed to auto-generate schedule: {str(e)}")

# ⚠️ FIX: Move this line OUTSIDE the function and to the module level
app.cli.add_command(schedule_cli)

prefs_cli = AppGroup('prefs', help='Preferences commands')
@prefs_cli.command("set", help="Set preferences for a staff user")
@click.argument("staff_id", type=int)
@click.option("--preferred", default="", help="Comma separated preferred shift types")
@click.option("--skills", default="", help="Comma separated skills")
@click.option("--unavailable", default="", help="Comma separated unavailable weekday ints")
@click.option("--max_hours", default=None, type=int, help="Max hours per week")
def prefs_set_command(staff_id, preferred, skills, unavailable, max_hours):
    _print_banner()
    prefs = [p for p in preferred.split(",") if p] if preferred else None
    skills_list = [s for s in skills.split(",") if s] if skills else None
    unavailable_list = [int(x) for x in unavailable.split(",") if x] if unavailable else None
    result = set_preferences(
        staff_id,
        preferred_shift_types=prefs,
        skills=skills_list,
        unavailable_days=unavailable_list,
        max_hours_per_week=max_hours,
    )
    print("✅ Preferences set:")
    print(result.get_json())

@prefs_cli.command("get", help="Get preferences for a staff user")
@click.argument("staff_id", type=int)
def prefs_get_command(staff_id):
    _print_banner()
    
    from App.controllers import get_user
    from App.models import Preferences
    
    user = get_user(staff_id)
    if not user:
        print(f"❌ User with ID {staff_id} not found")
        return
    if user.role != "staff":
        print(f"❌ User {user.username} is not a staff member")
        return
    
    # Get preferences directly from database to ensure we have the latest data
    prefs = Preferences.query.filter_by(staff_id=staff_id).first()
    
    if not prefs:
        print(f"✅ Preferences for {user.username}:")
        print("No specific preferences set")
    else:
        # Print in table format
        headers = ["Preference Type", "Value"]
        rows = []
        
        # Check if preferences have actual values
        if (hasattr(prefs, 'preferred_shift_types') and 
            prefs.preferred_shift_types is not None and 
            len(prefs.preferred_shift_types) > 0):
            rows.append(["Preferred Shift Types", ", ".join(prefs.preferred_shift_types)])
        else:
            rows.append(["Preferred Shift Types", "None specified"])
        
        if (hasattr(prefs, 'skills') and 
            prefs.skills is not None and 
            len(prefs.skills) > 0):
            rows.append(["Skills", ", ".join(prefs.skills)])
        else:
            rows.append(["Skills", "None specified"])
        
        # FIX: Handle None for unavailable_days
        if (hasattr(prefs, 'unavailable_days') and 
            prefs.unavailable_days is not None and 
            len(prefs.unavailable_days) > 0):
            days_map = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday", 
                       4: "Thursday", 5: "Friday", 6: "Saturday"}
            unavailable_days = [days_map.get(day, f"Day {day}") for day in prefs.unavailable_days]
            rows.append(["Unavailable Days", ", ".join(unavailable_days)])
        else:
            rows.append(["Unavailable Days", "None specified"])
        
        if hasattr(prefs, 'max_hours_per_week') and prefs.max_hours_per_week:
            rows.append(["Max Hours/Week", prefs.max_hours_per_week])
        else:
            rows.append(["Max Hours/Week", "Not set"])
        
        print(f"✅ Preferences for {user.username}:")
        if rows:
            _print_table(headers, rows)
        else:
            print("No specific preferences set")

@prefs_cli.command("list", help="List all preferences in the system")
def prefs_list_command():
    _print_banner()
    from App.models import Preferences
    all_prefs = Preferences.query.all()
    
    if not all_prefs:
        print("No preferences found in the system")
        return
    
    headers = ["Staff ID", "Staff Name", "Preferred Shifts", "Skills", "Max Hours"]
    rows = []
    
    for prefs in all_prefs:
        staff_name = getattr(prefs.staff, 'username', 'Unknown') if prefs.staff else 'Unknown'
        preferred = ", ".join(prefs.preferred_shift_types) if prefs.preferred_shift_types else "None"
        skills = ", ".join(prefs.skills) if prefs.skills else "None"
        max_hours = prefs.max_hours_per_week or "Not set"
        
        rows.append([prefs.staff_id, staff_name, preferred, skills, max_hours])
    
    print("📋 All Preferences in System:")
    _print_table(headers, rows)



app.cli.add_command(prefs_cli)

'''
Test Commands
'''
test = AppGroup('test', help='Testing commands') 

@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "App"]))
    
app.cli.add_command(test)