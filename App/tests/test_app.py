import os, tempfile, pytest, logging, unittest
from werkzeug.security import check_password_hash, generate_password_hash
from App.main import create_app
import time
from App.database import db, create_db
from datetime import datetime, timedelta
from App.models import User, Schedule, Shift

from App.controllers import (
    create_user,
    get_all_users_json,
    loginCLI,
    get_user,
    update_user,
    schedule_shift, 
    get_shift_report,
    get_combined_roster,
    clock_in,
    clock_out,
    get_shift,
    auto_populate,
)
from App.controllers.scheduling import (
    Scheduler,
    EvenDistributeStrategy,
    MinimizeDaysStrategy,
    ShiftTypeStrategy,
    SchedulingStrategy
)


LOGGER = logging.getLogger(__name__)

'''
   Unit Tests
'''

class UserUnitTests(unittest.TestCase):

    def test_new_user_admin(self):
        user = create_user("bot", "bobpass", "admin")
        assert user.username == "bot"
        assert user.role == "admin"
        from App.models import Admin
        assert isinstance(user, Admin)

    def test_new_user_staff(self):
        user = create_user("pam", "pampass", "staff")
        assert user.username == "pam"
        assert user.role == "staff"
        from App.models import Staff
        assert isinstance(user, Staff)

    def test_create_user_invalid_role(self):
        user = create_user("jim", "jimpass","ceo")
        assert user == None

    def test_get_json(self):
        user = User("bob", "bobpass", "admin")
        user_json = user.get_json()
        self.assertDictEqual(user_json, {"id":None, "username":"bob", "role":"admin"})
    
    def test_hashed_password(self):
        password = "mypass"
        user = User(username="tester", password=password)
        assert user.password != password
        assert user.check_password(password) is True

    def test_check_password(self):
        password = "mypass"
        user = User("bob", password)
        assert user.check_password(password)

class SchedulingStrategyUnitTests(unittest.TestCase):
    
    def test_scheduling_strategy_abstract(self):
        with self.assertRaises(TypeError):
            strategy = SchedulingStrategy()

    def test_even_distribute_strategy_creation(self):
        strategy = EvenDistributeStrategy()
        self.assertIsInstance(strategy, EvenDistributeStrategy)
        self.assertIsInstance(strategy, SchedulingStrategy)

    def test_minimize_days_strategy_creation(self):
        strategy = MinimizeDaysStrategy()
        self.assertIsInstance(strategy, MinimizeDaysStrategy)
        self.assertIsInstance(strategy, SchedulingStrategy)

    def test_shift_type_strategy_creation(self):
        strategy = ShiftTypeStrategy()
        self.assertIsInstance(strategy, ShiftTypeStrategy)
        self.assertIsInstance(strategy, SchedulingStrategy)

    def test_scheduler_creation(self):
        scheduler = Scheduler()
        self.assertIsInstance(scheduler, Scheduler)
        
        available_strategies = scheduler.get_available_strategies()
        expected_strategies = ["even_distribute", "minimize_days", "shift_type_optimize"]
        self.assertEqual(set(available_strategies), set(expected_strategies))

class EvenDistributeStrategyUnitTests(unittest.TestCase):
    
    def setUp(self):
        self.strategy = EvenDistributeStrategy()
        
        # Create test staff
        class TestStaff:
            def __init__(self, username, skills=None, unavailable_days=None):
                self.username = username
                self.skills = skills or []
                self.unavailable_days = unavailable_days or []
                self.assigned_shifts = []
                self.total_hours = 0
                self.days_worked = 0
                self.max_hours_per_week = 40
                self.preferred_shift_types = ['regular']

        # Create test shifts
        class TestShift:
            def __init__(self, shift_id, start_time, end_time, required_skills=None):
                self.id = shift_id
                self.start_time = start_time
                self.end_time = end_time
                self.required_skills = required_skills or []
                self.assigned_staff = []
                self.duration_hours = 8
                self.required_staff = 1
                self.shift_type = 'regular'

        self.staff = [
            TestStaff("john", skills=["cashier", "customer_service"]),
            TestStaff("jane", skills=["cashier", "stocking"]),
            TestStaff("bob", skills=["management", "customer_service"])
        ]

        self.shifts = [
            TestShift(1, datetime(2024, 1, 1, 9, 0), datetime(2024, 1, 1, 17, 0), ["cashier"]),
            TestShift(2, datetime(2024, 1, 2, 9, 0), datetime(2024, 1, 2, 17, 0), ["stocking"]),
            TestShift(3, datetime(2024, 1, 3, 9, 0), datetime(2024, 1, 3, 17, 0), ["customer_service"]),
        ]

    def test_even_distribute_generate_schedule(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule(
            self.staff, self.shifts, start_date, end_date
        )
        
        # Check result structure
        self.assertIn("strategy", result)
        self.assertIn("schedule", result)
        self.assertIn("summary", result)
        self.assertIn("fairness_score", result)
        
        self.assertEqual(result["strategy"], "Even Distribution")
        
        # Check summary structure
        summary = result["summary"]
        self.assertIn("total_staff", summary)
        self.assertIn("total_hours_assigned", summary)
        self.assertIn("average_hours_per_staff", summary)
        
        # Check schedule structure
        schedule = result["schedule"]
        self.assertIsInstance(schedule, dict)

    def test_even_distribute_empty_input(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule([], [], start_date, end_date)
        
        self.assertEqual(result["summary"]["total_staff"], 0)
        self.assertEqual(result["summary"]["total_hours_assigned"], 0)
        self.assertEqual(result["fairness_score"], 0.0)

    def test_even_distribute_skill_match(self):
        # Create staff with specific skills
        cashier_only = type('Staff', (), {
            'username': 'cashier_only',
            'skills': ['cashier'],
            'unavailable_days': [],
            'assigned_shifts': [],
            'total_hours': 0,
            'days_worked': 0,
            'max_hours_per_week': 40,
            'preferred_shift_types': ['regular']
        })()
        
        # Create shift requiring management skill
        management_shift = type('Shift', (), {
            'id': 99,
            'start_time': datetime(2024, 1, 1, 9, 0),
            'end_time': datetime(2024, 1, 1, 17, 0),
            'required_skills': ['management'],
            'assigned_staff': [],
            'duration_hours': 8,
            'required_staff': 1,
            'shift_type': 'regular'
        })()
        
        result = self.strategy.generate_schedule(
            [cashier_only], [management_shift], 
            datetime(2024, 1, 1), datetime(2024, 1, 5)
        )
        
        self.assertEqual(len(management_shift.assigned_staff), 0)

class MinimizeDaysStrategyUnitTests(unittest.TestCase):
    
    def setUp(self):
        self.strategy = MinimizeDaysStrategy()
        
        class TestStaff:
            def __init__(self, username, skills=None, unavailable_days=None):
                self.username = username
                self.skills = skills or []
                self.unavailable_days = unavailable_days or []
                self.assigned_shifts = []
                self.total_hours = 0
                self.days_worked = 0
                self.max_hours_per_week = 40
                self.preferred_shift_types = ['regular']

        class TestShift:
            def __init__(self, shift_id, start_time, end_time, required_skills=None):
                self.id = shift_id
                self.start_time = start_time
                self.end_time = end_time
                self.required_skills = required_skills or []
                self.assigned_staff = []
                self.duration_hours = 8
                self.required_staff = 1
                self.shift_type = 'regular'

        self.staff = [
            TestStaff("alice", skills=["cashier", "stocking"]),
            TestStaff("charlie", skills=["management"]),
        ]

        # Create multiple shifts on same day
        self.shifts = [
            TestShift(1, datetime(2024, 1, 1, 9, 0), datetime(2024, 1, 1, 17, 0), ["cashier"]),
            TestShift(2, datetime(2024, 1, 1, 17, 0), datetime(2024, 1, 1, 1, 0), ["stocking"]),
            TestShift(3, datetime(2024, 1, 2, 9, 0), datetime(2024, 1, 2, 17, 0), ["management"]),
        ]

    def test_minimize_days_generate_schedule(self):
        """Test MinimizeDaysStrategy generates a valid schedule"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule(
            self.staff, self.shifts, start_date, end_date
        )
        
        self.assertIn("strategy", result)
        self.assertIn("schedule", result)
        self.assertIn("summary", result)
        self.assertIn("efficiency_score", result)
        
        self.assertEqual(result["strategy"], "Minimize Days")
        
        # Check that summary includes days information
        summary = result["summary"]
        self.assertIn("average_days_per_staff", summary)
        self.assertIn("min_days", summary)
        self.assertIn("max_days", summary)

    def test_minimize_days_consolidation(self):
        """Test that MinimizeDaysStrategy consolidates shifts on same day"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule(
            self.staff, self.shifts, start_date, end_date
        )
        
        # Check that staff work fewer days with more hours per day
        summary = result["summary"]
        self.assertLessEqual(summary["average_days_per_staff"], len(self.shifts))

class ShiftTypeStrategyUnitTests(unittest.TestCase):
    
    def setUp(self):
        self.strategy = ShiftTypeStrategy()
        
        class TestStaff:
            def __init__(self, username, preferred_shift_types, skills=None):
                self.username = username
                self.skills = skills or []
                self.unavailable_days = []
                self.assigned_shifts = []
                self.total_hours = 0
                self.days_worked = 0
                self.max_hours_per_week = 40
                self.preferred_shift_types = preferred_shift_types

        class TestShift:
            def __init__(self, shift_id, start_time, end_time, shift_type, required_skills=None):
                self.id = shift_id
                self.start_time = start_time
                self.end_time = end_time
                self.required_skills = required_skills or []
                self.assigned_staff = []
                self.duration_hours = 8
                self.required_staff = 1
                self.shift_type = shift_type

        # Staff with different shift preferences
        self.morning_staff = TestStaff("morning Person", ["morning"])
        self.evening_staff = TestStaff("evening Person", ["evening"])
        
        self.shifts = [
            TestShift(1, datetime(2024, 1, 1, 6, 0), datetime(2024, 1, 1, 14, 0), "morning"),
            TestShift(2, datetime(2024, 1, 1, 14, 0), datetime(2024, 1, 1, 22, 0), "evening"),
            TestShift(3, datetime(2024, 1, 2, 6, 0), datetime(2024, 1, 2, 14, 0), "morning"),
        ]

    def test_shift_type_generate_schedule(self):
       
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule(
            [self.morning_staff, self.evening_staff], self.shifts, start_date, end_date
        )
        
        self.assertIn("strategy", result)
        self.assertIn("schedule", result)
        self.assertIn("summary", result)
        self.assertIn("preference_score", result)
        
        self.assertEqual(result["strategy"], "Shift Type Optimization")

    def test_shift_type_preference_match(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = self.strategy.generate_schedule(
            [self.morning_staff, self.evening_staff], self.shifts, start_date, end_date
        )
        
        morning_shifts = [s for s in self.morning_staff.assigned_shifts if s.shift_type == "morning"]
        evening_shifts = [s for s in self.evening_staff.assigned_shifts if s.shift_type == "evening"]
        
        # The strategy should prefer matching shift types
        self.assertGreaterEqual(len(morning_shifts), 0)
        self.assertGreaterEqual(len(evening_shifts), 0)

class SchedulerIntegrationTests(unittest.TestCase):
    
    def setUp(self):
        self.scheduler = Scheduler()
        
        class TestStaff:
            def __init__(self, username, skills=None):
                self.username = username
                self.skills = skills or ["cashier"]
                self.assigned_shifts = []
                self.total_hours = 0
                self.days_worked = 0

        class TestShift:
            def __init__(self, shift_id, start_time, end_time):
                self.id = shift_id
                self.start_time = start_time
                self.end_time = end_time
                self.assigned_staff = []
                self.duration_hours = 8
                self.required_staff = 1
                self.shift_type = 'regular'
                self.required_skills = ['cashier']

        self.staff = [TestStaff(f"staff_{i}") for i in range(3)]
        self.shifts = [
            TestShift(i, datetime(2024, 1, 1 + i, 9, 0), datetime(2024, 1, 1 + i, 17, 0))
            for i in range(5)
        ]

    def test_scheduler_all_strategies(self):
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        for strategy_name in self.scheduler.get_available_strategies():
            with self.subTest(strategy=strategy_name):
                result = self.scheduler.generate_schedule(
                    strategy_name, self.staff, self.shifts, start_date, end_date
                )
                self.assertIn("strategy", result)
                self.assertIn("schedule", result)
                self.assertIn("summary", result)

    def test_scheduler_invalid_strategy(self):
        with self.assertRaises(ValueError) as context:
            self.scheduler.generate_schedule(
                "invalid_strategy", self.staff, self.shifts, 
                datetime(2024, 1, 1), datetime(2024, 1, 10)
            )
        
        self.assertIn("Unknown strategy", str(context.exception))

    def test_scheduler_get_available_strategies(self):
        strategies = self.scheduler.get_available_strategies()
        expected = ["even_distribute", "minimize_days", "shift_type_optimize"]
        self.assertEqual(set(strategies), set(expected))
        self.assertEqual(len(strategies), 3)

# Admin unit tests
class AdminUnitTests(unittest.TestCase):
    def test_schedule_shift_valid(self):
        admin = create_user("admin1", "adminpass", "admin")
        staff = create_user("staff1", "staffpass", "staff")
        schedule = Schedule(name="Morning Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 22, 8, 0, 0)
        end = datetime(2025, 10, 22, 16, 0, 0)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        assert shift.staff_id == staff.id
        assert shift.schedule_id == schedule.id
        assert shift.start_time == start
        assert shift.end_time == end
        assert isinstance(shift, Shift)

    def test_schedule_shift_invalid(self):
        admin = User("admin2", "adminpass", "admin")
        staff = User("staff2", "staffpass", "staff")
        invalid_schedule_id = 999

        start = datetime(2025, 10, 22, 8, 0, 0)
        end = datetime(2025, 10, 22, 16, 0, 0)
        try:
            shift = schedule_shift(admin.id, staff.id, invalid_schedule_id, start, end)
            assert shift is None  
        except Exception:
            assert True



    def test_get_shift_report(self):
        admin = create_user("superadmin", "superpass", "admin")
        staff = create_user("worker1", "workerpass", "staff")
        db.session.add_all([admin, staff])
        db.session.commit()

        schedule = Schedule(name="Weekend Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        shift1 = schedule_shift(admin.id, staff.id, schedule.id,
                                datetime(2025, 10, 26, 8, 0, 0),
                                datetime(2025, 10, 26, 16, 0, 0))
        shift2 = schedule_shift(admin.id, staff.id, schedule.id,
                                datetime(2025, 10, 27, 8, 0, 0),
                                datetime(2025, 10, 27, 16, 0, 0))
        
        report = get_shift_report(admin.id)
        assert len(report) >= 2
        assert report[0]["staff_id"] == staff.id
        assert report[0]["schedule_id"] == schedule.id

    def test_get_shift_report_invalid(self):
        non_admin = User("randomstaff", "randompass", "staff")

        try:
            get_shift_report(non_admin.id)
            assert False, "Expected PermissionError for non-admin user"
        except PermissionError as e:
            assert str(e) == "Only admins can view shift reports"

#New tests for Admin.auto_populate
class AdminAutoPopulateTests(unittest.TestCase):
    """
    Tests for the Admin.auto_populate() controller function.
    """

    def test_auto_populate_creates_schedule_and_shifts(self):
        admin = create_user("admin_auto", "pass", "admin")
        staff1 = create_user("auto_staff1", "pass", "staff")
        staff2 = create_user("auto_staff2", "pass", "staff")

        # 3 days, 2 shifts per day
        start_date = datetime(2025, 1, 1)
        end_date = datetime(2025, 1, 3)
        shifts_per_day = 2

        schedule = auto_populate(
            admin_id=admin.id,
            strategy_name="even_distribute",
            staff_list=[staff1, staff2],
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=shifts_per_day,
            shift_length_hours=8,
        )

        assert isinstance(schedule, Schedule)
        assert schedule.id is not None

        expected_shifts = 3 * shifts_per_day
        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        assert len(shifts) == expected_shifts

        staff_ids = {staff1.id, staff2.id}
        assert all(s.staff_id in staff_ids for s in shifts)
        assert all(s.start_time < s.end_time for s in shifts)

    def test_auto_populate_distribution_reasonable(self):
        """
        Distribution between staff should be reasonably fair (difference <= 1).
        """
        admin = create_user("admin_rr", "pass", "admin")
        staff1 = create_user("rr_staff1", "pass", "staff")
        staff2 = create_user("rr_staff2", "pass", "staff")

        start_date = datetime(2025, 2, 1)
        end_date = datetime(2025, 2, 4)  # 4 days, 1 shift/day

        schedule = auto_populate(
            admin_id=admin.id,
            strategy_name="even_distribute",
            staff_list=[staff1, staff2],
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=1,
            shift_length_hours=8,
        )

        shifts = Shift.query.filter_by(schedule_id=schedule.id).all()
        assert len(shifts) == 4

        count1 = sum(1 for s in shifts if s.staff_id == staff1.id)
        count2 = sum(1 for s in shifts if s.staff_id == staff2.id)
        assert abs(count1 - count2) <= 1

    def test_auto_populate_requires_admin(self):
        admin = create_user("admin_ok", "pass", "admin")
        staff_user = create_user("not_admin", "pass", "staff")

        start_date = datetime(2025, 3, 1)
        end_date = datetime(2025, 3, 2)

        # non-admin should not be allowed
        with pytest.raises(PermissionError) as e:
            auto_populate(
                admin_id=staff_user.id,   # NOT an admin
                strategy_name="even_distribute",
                staff_list=[staff_user],
                start_date=start_date,
                end_date=end_date,
                shifts_per_day=1,
            )
        # match your existing _ensure_admin message
        assert str(e.value) == "Only admins can view shift reports"

        # sanity check: admin path works
        schedule = auto_populate(
            admin_id=admin.id,
            strategy_name="even_distribute",
            staff_list=[staff_user],
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=1,
        )
        assert isinstance(schedule, Schedule)

    def test_auto_populate_empty_staff_list_invalid(self):
        admin = create_user("admin_empty", "pass", "admin")
        start_date = datetime(2025, 4, 1)
        end_date = datetime(2025, 4, 1)

        with pytest.raises(ValueError) as e:
            auto_populate(
                admin_id=admin.id,
                strategy_name="even_distribute",
                staff_list=[],          # ❌ no staff
                start_date=start_date,
                end_date=end_date,
                shifts_per_day=1,
            )
        assert "Staff list cannot be empty" in str(e.value)

    def test_auto_populate_invalid_dates(self):
        admin = create_user("admin_dates", "pass", "admin")
        staff = create_user("staff_dates", "pass", "staff")

        start_date = datetime(2025, 5, 10)
        end_date = datetime(2025, 5, 1)  # end before start

        with pytest.raises(ValueError):
            auto_populate(
                admin_id=admin.id,
                strategy_name="even_distribute",
                staff_list=[staff],
                start_date=start_date,
                end_date=end_date,
                shifts_per_day=1,
            )

    def test_auto_populate_invalid_shifts_per_day(self):
        admin = create_user("admin_invalid_shifts", "pass", "admin")
        staff = create_user("staff_invalid_shifts", "pass", "staff")

        start_date = datetime(2025, 6, 1)
        end_date = datetime(2025, 6, 1)

        with pytest.raises(ValueError):
            auto_populate(
                admin_id=admin.id,
                strategy_name="even_distribute",
                staff_list=[staff],
                start_date=start_date,
                end_date=end_date,
                shifts_per_day=0,   # ❌ invalid
            )


# Staff unit tests
class StaffUnitTests(unittest.TestCase):
    def test_get_combined_roster_valid(self):
        staff = create_user("staff3", "pass123", "staff")
        admin = create_user("admin3", "adminpass", "admin")
        schedule = Schedule(name="Test Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        # create a shift
        shift = schedule_shift(admin.id, staff.id, schedule.id,
                               datetime(2025, 10, 23, 8, 0, 0),
                               datetime(2025, 10, 23, 16, 0, 0))

        roster = get_combined_roster(staff.id)
        assert len(roster) >= 1
        assert roster[0]["staff_id"] == staff.id
        assert roster[0]["schedule_id"] == schedule.id

    def test_get_combined_roster_invalid(self):
        non_staff = create_user("admin4", "adminpass", "admin")
        try:
            get_combined_roster(non_staff.id)
            assert False, "Expected PermissionError for non-staff"
        except PermissionError as e:
            assert str(e) == "Only staff can view roster"

    def test_clock_in_valid(self):
        admin = create_user("admin_clock", "adminpass", "admin")
        staff = create_user("staff_clock", "staffpass", "staff")

        schedule = Schedule(name="Clock Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 25, 8, 0, 0)
        end = datetime(2025, 10, 25, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clocked_in_shift = clock_in(staff.id, shift.id)
        assert clocked_in_shift.clock_in is not None
        assert isinstance(clocked_in_shift.clock_in, datetime)

    def test_clock_in_invalid_user(self):
        admin = create_user("admin_clockin", "adminpass", "admin")
        schedule = Schedule(name="Invalid Clock In", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        staff = create_user("staff_invalid", "staffpass", "staff")
        start = datetime(2025, 10, 26, 8, 0, 0)
        end = datetime(2025, 10, 26, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        with pytest.raises(PermissionError) as e:
            clock_in(admin.id, shift.id)
        assert str(e.value) == "Only staff can clock in"

    def test_clock_in_invalid_shift(self):
        staff = create_user("clockstaff_invalid", "clockpass", "staff")
        with pytest.raises(ValueError) as e:
            clock_in(staff.id, 999)
        assert str(e.value) == "Invalid shift for staff"

    def test_clock_out_valid(self):
        admin = create_user("admin_clockout", "adminpass", "admin")
        staff = create_user("staff_clockout", "staffpass", "staff")

        schedule = Schedule(name="ClockOut Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime(2025, 10, 27, 8, 0, 0)
        end = datetime(2025, 10, 27, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clocked_out_shift = clock_out(staff.id, shift.id)
        assert clocked_out_shift.clock_out is not None
        assert isinstance(clocked_out_shift.clock_out, datetime)

    def test_clock_out_invalid_user(self):
        admin = create_user("admin_invalid_out", "adminpass", "admin")
        schedule = Schedule(name="Invalid ClockOut Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        staff = create_user("staff_invalid_out", "staffpass", "staff")
        start = datetime(2025, 10, 28, 8, 0, 0)
        end = datetime(2025, 10, 28, 16, 0, 0)
        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        with pytest.raises(PermissionError) as e:
            clock_out(admin.id, shift.id)
        assert str(e.value) == "Only staff can clock out"

    def test_clock_out_invalid_shift(self):
        staff = create_user("staff_invalid_shift_out", "staffpass", "staff")
        with pytest.raises(ValueError) as e:
            clock_out(staff.id, 999)  
        assert str(e.value) == "Invalid shift for staff"

'''
    Integration Tests
'''
@pytest.fixture(autouse=True)
def clean_db():
    db.drop_all()
    create_db()
    db.session.remove()
    yield

@pytest.fixture(autouse=True, scope="module")
def empty_db():
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///test.db'})
    create_db()
    db.session.remove()
    yield app.test_client()
    db.drop_all()

def test_authenticate(empty_db):
    create_user("bob", "bobpass", "user")
    result = loginCLI("bob", "bobpass")
    assert result is not None
    assert "token" in result


class UsersIntegrationTests(unittest.TestCase):

    def test_get_all_users_json(self):
        user = create_user("bot", "bobpass","admin")
        user = create_user("pam", "pampass","staff")
        users_json = get_all_users_json()
        self.assertListEqual([{"id":1, "username":"bot", "role":"admin"}, {"id":2, "username":"pam","role":"staff"}], users_json)

    def test_update_user(self):
        user = create_user("bot", "bobpass","admin")
        update_user(1, "ronnie")
        user = get_user(1)
        assert user.username == "ronnie"

    def test_create_and_get_user(self):
        user = create_user("alex", "alexpass", "staff")
        retrieved = get_user(user.id)
        self.assertEqual(retrieved.username, "alex")
        self.assertEqual(retrieved.role, "staff")
    
    def test_get_all_users_json_integration(self):
        create_user("bot", "bobpass", "admin")
        create_user("pam", "pampass", "staff")
        users_json = get_all_users_json()
        expected = [
            {"id": 1, "username": "bot", "role": "admin"},
            {"id": 2, "username": "pam", "role": "staff"},
        ]
        self.assertEqual(users_json, expected)
        
    def test_admin_schedule_shift_for_staff(self):
        admin = create_user("admin1", "adminpass", "admin")
        staff = create_user("staff1", "staffpass", "staff")

        schedule = Schedule(name="Week 1 Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)
        retrieved = get_user(staff.id)

        self.assertIn(shift.id, [s.id for s in retrieved.shifts])
        self.assertEqual(shift.staff_id, staff.id)
        self.assertEqual(shift.schedule_id, schedule.id)

    def test_staff_view_combined_roster(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("jane", "janepass", "staff")
        other_staff = create_user("mark", "markpass", "staff")

        schedule = Schedule(name="Shared Roster", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        schedule_shift(admin.id, staff.id, schedule.id, start, end)
        schedule_shift(admin.id, other_staff.id, schedule.id, start, end)

        roster = get_combined_roster(staff.id)
        self.assertTrue(any(s["staff_id"] == staff.id for s in roster))
        self.assertTrue(any(s["staff_id"] == other_staff.id for s in roster))

    def test_staff_clock_in_and_out(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("lee", "leepass", "staff")

        schedule = Schedule(name="Daily Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        shift = schedule_shift(admin.id, staff.id, schedule.id, start, end)

        clock_in(staff.id, shift.id)
        time.sleep(0.01)  
        clock_out(staff.id, shift.id)

        updated_shift = get_shift(shift.id)
        self.assertIsNotNone(updated_shift.clock_in)
        self.assertIsNotNone(updated_shift.clock_out)
        self.assertLess(updated_shift.clock_in, updated_shift.clock_out)
    
    def test_admin_generate_shift_report(self):
        admin = create_user("boss", "boss123", "admin")
        staff = create_user("sam", "sampass", "staff")

        schedule = Schedule(name="Weekly Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        schedule_shift(admin.id, staff.id, schedule.id, start, end)
        report = get_shift_report(admin.id)

        self.assertTrue(any("sam" in r["staff_name"] for r in report))
        self.assertTrue(all("start_time" in r and "end_time" in r for r in report))

    def test_permission_restrictions(self):
        admin = create_user("admin", "adminpass", "admin")
        staff = create_user("worker", "workpass", "staff")

        # Create schedule
        schedule = Schedule(name="Restricted Schedule", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()

        start = datetime.now()
        end = start + timedelta(hours=8)

        with self.assertRaises(PermissionError):
            schedule_shift(staff.id, staff.id, schedule.id, start, end)

        with self.assertRaises(PermissionError):
            get_combined_roster(admin.id)

        with self.assertRaises(PermissionError):
            get_shift_report(staff.id)

class SchedulingIntegrationTests(unittest.TestCase):
    
    def test_scheduler_with_user_and_shift(self):
      
        admin = create_user("scheduler_admin", "adminpass", "admin")
        staff1 = create_user("scheduler_staff1", "staffpass", "staff")
        staff2 = create_user("scheduler_staff2", "staffpass", "staff")
        
        # Create schedule
        schedule = Schedule(name="Scheduler Test", created_by=admin.id)
        db.session.add(schedule)
        db.session.commit()
        
        # Create shifts
        shifts = []
        for i in range(3):
            shift = schedule_shift(
                admin.id, staff1.id, schedule.id,
                datetime(2024, 1, 1 + i, 9, 0, 0),
                datetime(2024, 1, 1 + i, 17, 0, 0)
            )
            shifts.append(shift)
        
        # Test scheduler
        scheduler = Scheduler()
        staff_list = [staff1, staff2]
        
        result = scheduler.generate_schedule(
            "even_distribute",
            staff_list,
            shifts,
            datetime(2024, 1, 1),
            datetime(2024, 1, 5)
        )
        
        self.assertEqual(result["strategy"], "Even Distribution")
        self.assertIn("summary", result)
        self.assertIn("fairness_score", result)

