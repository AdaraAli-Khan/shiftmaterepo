from App.database import db
from sqlalchemy import JSON


class Preferences(db.Model):
    __tablename__ = 'preferences'

    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)

    # Stored as JSON arrays where appropriate
    preferred_shift_types = db.Column(JSON, nullable=True)  # e.g. ["morning", "evening"]
    skills = db.Column(JSON, nullable=True)  # e.g. ["cashier", "stocking"]
    unavailable_days = db.Column(JSON, nullable=True)  # list of weekday ints [0..6]
    max_hours_per_week = db.Column(db.Integer, nullable=True, default=40)

    def get_json(self):
        return {
            "id": self.id,
            "staff_id": self.staff_id,
            "preferred_shift_types": self.preferred_shift_types or [],
            "skills": self.skills or [],
            "unavailable_days": self.unavailable_days or [],
            "max_hours_per_week": self.max_hours_per_week if self.max_hours_per_week is not None else 40,
        }
