![Tests](https://github.com/uwidcit/flaskmvc/actions/workflows/dev.yml/badge.svg)

# ShiftMate 3.0 — Flask MVC Workforce Scheduler
ShiftMate 3.0 is a lightweight Flask-based workforce scheduling system for creating staff accounts, assigning shifts, tracking time, and generating simple reports. It includes automated scheduling strategies (even distribution, minimize days, and shift-type optimization) and per-staff preferences used by the scheduler.

Key features:
- Create/manage users (admin & staff)
- Create schedules and assign shifts
- Clock in / clock out and basic attendance reporting
- Auto-generate schedules with multiple strategies
- Per-staff preferences influencing schedule generation

Demo & Postman: [Demo](https://dcit-flaskmvc.herokuapp.com/) · [Postman Collection](https://documenter.getpostman.com/view/583570/2s83zcTnEJ)


# Dependencies
* Python3/pip3
* Packages listed in requirements.txt

# Installing Dependencies
```bash
$ pip install -r requirements.txt
```

# Configuration Management


Configuration information such as the database url/port, credentials, API keys etc are to be supplied to the application. However, it is bad practice to stage production information in publicly visible repositories.
Instead, all config is provided by a config file or via [environment variables](https://linuxize.com/post/how-to-set-and-list-environment-variables-in-linux/).

## In Development

When running the project in a development environment (such as gitpod) the app is configured via default_config.py file in the App folder. By default, the config for development uses a sqlite database.

default_config.py
```python
SQLALCHEMY_DATABASE_URI = "sqlite:///temp-database.db"
SECRET_KEY = "secret key"
JWT_ACCESS_TOKEN_EXPIRES = 7
ENV = "DEVELOPMENT"
```

These values would be imported and added to the app in load_config() function in config.py

config.py
```python
# must be updated to inlude addtional secrets/ api keys & use a gitignored custom-config file instad
def load_config():
    config = {'ENV': os.environ.get('ENV', 'DEVELOPMENT')}
    delta = 7
    if config['ENV'] == "DEVELOPMENT":
        from .default_config import JWT_ACCESS_TOKEN_EXPIRES, SQLALCHEMY_DATABASE_URI, SECRET_KEY
        config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        config['SECRET_KEY'] = SECRET_KEY
        delta = JWT_ACCESS_TOKEN_EXPIRES
...
```

## In Production

When deploying your application to production/staging you must pass
in configuration information via environment tab of your render project's dashboard.

![perms](./images/fig1.png)

# CLI Quick Reference

The application exposes a number of convenient CLI groups via `wsgi.py`. Use `flask <group> <command>`.

Authentication
- `flask auth login <username> <password>` — login and save a JWT token for CLI use
- `flask auth logout <username>` — logout (removes saved token file)

User management
- `flask user create <username> <password> <role>` — create a user (role: `admin` or `staff`)
- `flask user list [string|json]` — list users in text or JSON format

Shifts
- `flask shift schedule <staff_id> <schedule_id> <start_iso> <end_iso>` — schedule a shift (admin)
- `flask shift roster` — show combined roster for logged-in staff
- `flask shift clockin <shift_id>` — clock in (staff)
- `flask shift clockout <shift_id>` — clock out (staff)
- `flask shift report` — view shift report (admin)

Schedule management
- `flask schedule create <name>` — create a schedule (admin)
- `flask schedule list` — list schedules (admin)
- `flask schedule view <schedule_id>` — view a schedule and its shifts (admin)
- `flask schedule auto <strategy> [--days N]` — auto-generate a schedule using a strategy (admin)
    - Example strategies: `even-distribute`, `minimize-days`, `preference-based`
    - Example: `flask schedule auto even-distribute --days 14`

Preferences (per-staff)
The `prefs` CLI uses flags for each preference field. Example:

```bash
# set preferences using CLI flags
flask prefs set <staff_id> --preferred "morning,evening" --skills "cashier" --unavailable "0,6" --max_hours 40

# get preferences
flask prefs get <staff_id>
```

Note: the `--preferred`, `--skills`, and `--unavailable` flags accept comma-separated values when using the CLI; the controllers accept Python lists when called from code.


# Running the Project

_For development run the serve command (what you execute):_
```bash
$ flask run
```

_For production using gunicorn (what the production server executes):_
```bash
$ gunicorn wsgi:app
```

# Deploying
You can deploy your version of this app to render by clicking on the "Deploy to Render" link above.

# Initializing the Database
When connecting the project to a fresh empty database ensure the appropriate configuration is set then file then run the following command. This must also be executed once when running the app on heroku by opening the heroku console, executing bash and running the command in the dyno.

This creates 4 users id 1 is the admin, id 2 and 3 are staff and 4 is a user
```bash
$ flask init
```
# User Management

Create Users

After flask type user create then add the username, the password and the role of the user (either admin, staff or user)

```bash
flask user create admin1 adminpass admin
```
List users
```bash
flask user list string
flask user list json
```
# Managing shifts

To Schedule shifts (Admin only)

After flask type shift  schedule the staff id, the schedule idand the start and end of the shift in the ISO 8601 DateTime with time format( can copy the formant below and edit it)

```bash
flask shift schedule 2 1 2025-10-01T09:00:00 2025-10-01T17:00:00
```
View Roster (Staff only)

After flask type shift roster to for the logged in staff

```bash
flask shift roster 
```
Clockin and Clockout(Staff only)

After flask type shift clockin or clockoutand the shift id

```bash
flask shift clockin 1
flask shift clockout 1
```

Shift Report (Admin only)

After flask  type shift report 

```bash
flask shift report 
```

# Managing schedule

Create Schedule(Admin only)

After flask type schedule, create and the title 

```bash
flask schedule create "April Week 2" 
```

List All Schedules(Admin only)

After flask  type schedule  list 

```bash
flask schedule list 
```
View a Schedule (Admin only)

After flask type schedule view and the schedule id 

```bash
flask schedule view 1 
```

# Preferences
Per-staff preferences influence scheduling decisions. Stored fields:
- `preferred_shift_types` — list of strings (e.g. `['morning','evening']`)
- `skills` — list of strings
- `unavailable_days` — list of weekday integers `0..6` (Sunday=0)
- `max_hours_per_week` — integer (0..168)

Use the controller helpers in `App/controllers/preferences.py`: `get_preferences(staff_id)` and `set_preferences(staff_id, ...)`.

CLI examples (use flags):
```bash
flask prefs set 5 --preferred "morning,evening" --skills "cashier" --unavailable "0,6" --max_hours 40
flask prefs get 5
```

# Database Migrations
If changes to the models are made, the database must be'migrated' so that it can be synced with the new models.
Then execute following commands using manage.py. More info [here](https://flask-migrate.readthedocs.io/en/latest/)

```bash
$ flask db init
$ flask db migrate
$ flask db upgrade
$ flask db --help
```

# Testing

## Unit & Integration
Unit and Integration tests are created in the App/test. You can then create commands to run them. Look at the unit test command in wsgi.py for example

```python
@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "User"]))
```

# Testing commands

The `wsgi.py` `test` group exposes a small helper for running the `User` test group:

```bash
# Run all user tests
flask test user

# Run only user unit tests
flask test user unit

# Run only user integration tests
flask test user int
```

For other groups (preferences, scheduling, etc.) use `pytest` directly and filter by test class name with `-k`.

```bash
# run all tests
pytest

# run only preference unit tests (from `App/tests/test_app.py`)
pytest -k PreferencesUnitTests

# run only preference integration tests
pytest -k PreferencesIntegrationTests
```

## Test Coverage

You can generate a report on your test coverage via the following command

```bash
$ coverage report
```

You can also generate a detailed html report in a directory named htmlcov with the following comand

```bash
$ coverage html
```

### Notes
- The CLI `prefs` commands are convenience wrappers — when calling the controllers directly from Python pass proper Python lists (not comma-separated strings).
- If you add or change models, run the Flask-Migrate commands to create and apply migrations.
- Keep `App/models/__init__.py` up-to-date so in-memory DB creation for tests imports all models before `create_all()`.

# Troubleshooting

## Views 404ing

If your newly created views are returning 404 ensure that they are added to the list in main.py.

```python
from App.views import (
    user_views,
    index_views
)

# New views must be imported and added to this list
views = [
    user_views,
    index_views
]
```

## Cannot Update Workflow file

If you are running into errors in gitpod when updateding your github actions file, ensure your [github permissions](https://gitpod.io/integrations) in gitpod has workflow enabled ![perms](./images/gitperms.png)

## Database Issues

If you are adding models you may need to migrate the database with the commands given in the previous database migration section. Alternateively you can delete you database file.
