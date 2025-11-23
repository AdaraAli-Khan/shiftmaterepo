from datetime import datetime
from App.database import db

class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey("schedule.id"), nullable=True)
    shift_type_id = db.Column(db.Integer, db.ForeignKey("shift_type.id"), nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    clock_in = db.Column(db.DateTime, nullable=True)
    clock_out = db.Column(db.DateTime, nullable=True)
    staff = db.relationship("Staff", backref="shifts", foreign_keys=[staff_id])

    def get_duration(self):
        """Returns duration in hours"""
        duration = self.end_time - self.start_time
        return duration.total_seconds() / 3600

    def get_json(self):
        return {
            "id": self.id,
            "staff_id": self.staff_id,
            "staff_name": self.staff.username if self.staff else None,
            "start_time": self.start_time.isoformat(),
            "schedule_id": self.schedule_id,
            "end_time": self.end_time.isoformat(),
            "clock_in": self.clock_in.isoformat() if self.clock_in else None,
            "clock_out": self.clock_out.isoformat() if self.clock_out else None
        }
