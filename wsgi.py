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

app = create_app()
migrate = get_migrate(app)

@app.cli.command("init", help="Creates and initializes the database")
def init():
    initialize()
    print('database intialized')

auth_cli = AppGroup('auth', help='Authentication commands')

@auth_cli.command("login", help="Login and get JWT token")
@click.argument("username")
@click.argument("password")
def login_command(username, password):
    result = loginCLI(username, password)
    if result["message"] == "Login successful":
        token = result["token"]
        with open("active_token.txt", "w") as f:
            f.write(token)
        print(f"✅ {result['message']}! JWT token saved for CLI use.")
    else:
        print(f"⚠️ {result['message']}")

@auth_cli.command("logout", help="Logout a user by username")
@click.argument("username")
def logout_command(username):
    from App.controllers.auth import logout
    result = logout(username)
    if os.path.exists("active_token.txt"):
        os.remove("active_token.txt")
    print(result["message"])
    
app.cli.add_command(auth_cli)


user_cli = AppGroup('user', help='User object commands') 

@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
@click.argument("role", default="staff")
def create_user_command(username, password, role):
    create_user(username, password, role)
    print(f'{username} created!')

@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    if format == 'string':
        print(get_all_users())
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
    start_time = datetime.fromisoformat(start)
    end_time = datetime.fromisoformat(end)
    shift = schedule_shift(admin.id, staff_id, schedule_id, start_time, end_time)
    print(f"✅ Shift scheduled under Schedule {schedule_id} by {admin.username}:")
    print(shift.get_json())



@shift_cli.command("roster", help="Staff views combined roster")
def roster_command():
    staff = require_staff_login()
    roster = get_combined_roster(staff.id)
    print(f"📋 Roster for {staff.username}:")
    print(roster)


@shift_cli.command("clockin", help="Staff clocks in")
@click.argument("shift_id", type=int)
def clockin_command(shift_id):
    staff = require_staff_login()
    shift = clock_in(staff.id, shift_id)
    print(f"🕒 {staff.username} clocked in: {shift.get_json()}")



@shift_cli.command("clockout", help="Staff clocks out")
@click.argument("shift_id", type=int)
def clockout_command(shift_id):
    staff = require_staff_login()
    shift = clock_out(staff.id, shift_id)
    print(f"🕕 {staff.username} clocked out: {shift.get_json()}")


@shift_cli.command("report", help="Admin views shift report")
def report_command():
    admin = require_admin_login()
    report = get_shift_report(admin.id)
    print(f"📊 Shift report for {admin.username}:")
    print(report)

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
    schedule = Schedule(name=name, created_by=admin.id)
    db.session.add(schedule)
    db.session.commit()
    print(f"✅ Schedule created: {schedule.get_json()}")


@schedule_cli.command("list", help="List all schedules")
def list_schedules_command():
    from App.models import Schedule
    admin = require_admin_login()
    schedules = Schedule.query.all()
    print(f"✅ Found {len(schedules)} schedule(s):")
    for s in schedules:
        print(s.get_json())


@schedule_cli.command("view", help="View a schedule and its shifts")
@click.argument("schedule_id", type=int)
def view_schedule_command(schedule_id):
    from App.models import Schedule
    admin = require_admin_login()
    schedule = db.session.get(Schedule, schedule_id)
    if not schedule:
        print("⚠️ Schedule not found.")
    else:
        print(f"✅ Viewing schedule {schedule_id}:")
        print(schedule.get_json())


@schedule_cli.command("auto", help="Auto-generate schedule using AI strategies (SPECIAL FEATURE)")
@click.argument("strategy", default="even-distribute")
@click.option("--days", default=7, help="Number of days to schedule")
def auto_schedule_command(strategy, days):
    """
    Auto-populate schedule using intelligent scheduling strategies.
    
    Strategies available:
    - even-distribute: Fairly distribute shifts across all staff
    - minimize-days: Minimize total days each staff member works
    - preference-based: Match shifts to staff shift type preferences
    
    Example:
    $ flask schedule auto even-distribute --days 14
    """
    from App.controllers.scheduling import schedule_client
    from App.models import Staff
    from datetime import datetime, timedelta
    
    admin = require_admin_login()
    
    # Get all available staff
    staff_list = Staff.query.all()
    if not staff_list:
        print("No staff available. Create staff members first.")
        return
    
    # Set date range
    start_date = datetime.now().date()
    end_date = start_date + timedelta(days=days)
    
    # Validate strategy
    available = schedule_client.get_available_strategies()
    if strategy not in available:
        print(f" Invalid strategy. Available: {', '.join(available)}")
        return
    
    try:
        print(f" Generating {strategy} schedule for {len(staff_list)} staff over {days} days...")
        result = schedule_client.auto_populate(
            admin_id=admin.id,
            strategy_name=strategy,
            staff_list=staff_list,
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=2
        )
        
        print(f"\n Schedule auto-generated using '{strategy}' strategy!")
        print(f" Schedule ID: {result['schedule'].id}")
        print(f"Performance Score: {result['score']:.2f}")
        print(f"\ Summary:\n{result['summary']}")
        
    except Exception as e:
        print(f" Failed to auto-generate schedule: {str(e)}")

app.cli.add_command(schedule_cli)
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
