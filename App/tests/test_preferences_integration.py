import unittest
from datetime import datetime

from App.main import create_app
from App.database import db, create_db
from App.controllers import create_user
from App.controllers.preferences import set_preferences, get_preferences
from App.controllers.scheduling import Scheduler


class PreferencesIntegrationTests(unittest.TestCase):
    def setUp(self):
        # create app and push context
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
        self.ctx = self.app.app_context()
        self.ctx.push()

        # fresh database for each test
        db.drop_all()
        create_db()
        # create an admin for potential schedule creation if needed
        self.admin = create_user("pref_admin", "adminpass", "admin")

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_preferences_persist_and_staff_relationship(self):
        staff = create_user("int_pref_staff", "pass", "staff")

        set_preferences(
            staff.id,
            preferred_shift_types=["morning"],
            skills=["cashier"],
            unavailable_days=[6],
            max_hours_per_week=20,
        )

        # reload staff from DB and check relationship
        from App.models import Staff

        refreshed = Staff.query.get(staff.id)
        self.assertIsNotNone(refreshed.preferences)
        self.assertEqual(refreshed.preferred_shift_types, ["morning"])

        got = get_preferences(staff.id)
        self.assertEqual(got["skills"], ["cashier"])

    def test_preferences_used_by_scheduler(self):
        # two staff with different shift type preferences
        staff1 = create_user("s1", "pass", "staff")
        staff2 = create_user("s2", "pass", "staff")

        set_preferences(staff1.id, preferred_shift_types=["morning"], skills=[], unavailable_days=[], max_hours_per_week=40)
        set_preferences(staff2.id, preferred_shift_types=["evening"], skills=[], unavailable_days=[], max_hours_per_week=40)

        # create simple in-memory shift templates (not persisted)
        class ShiftTemplate:
            def __init__(self, id, start, end, shift_type):
                self.id = id
                self.start_time = start
                self.end_time = end
                self.shift_type = shift_type
                self.required_skills = []
                self.assigned_staff = []
                self.duration_hours = 8
                self.required_staff = 1

        shifts = [
            ShiftTemplate(1, datetime(2025, 1, 1, 9, 0), datetime(2025, 1, 1, 17, 0), "morning"),
            ShiftTemplate(2, datetime(2025, 1, 1, 17, 0), datetime(2025, 1, 1, 23, 0), "evening"),
        ]

        scheduler = Scheduler()

        # pass ORM staff objects directly to the scheduler
        staff_list = [staff1, staff2]
        result = scheduler.generate_schedule("shift_type_optimize", staff_list, shifts, datetime(2025, 1, 1), datetime(2025, 1, 2))

        self.assertEqual(result["strategy"], "Shift Type Optimization")

        morning_assigned = any(getattr(s, 'shift_type', '') == 'morning' for s in getattr(staff_list[0], 'assigned_shifts', []))
        evening_assigned = any(getattr(s, 'shift_type', '') == 'evening' for s in getattr(staff_list[1], 'assigned_shifts', []))

        # At least one of the staff should receive an assignment matching their preference
        self.assertTrue(morning_assigned or evening_assigned)


if __name__ == '__main__':
    unittest.main()
