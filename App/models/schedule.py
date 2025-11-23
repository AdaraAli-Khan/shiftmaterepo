from datetime import datetime
from App.database import db

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=True)
    name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    shifts = db.relationship("Shift", backref="schedule", lazy=True, cascade="all, delete-orphan")

    def shift_count(self):
        return len(self.shifts)
    
    def add_shift(self, shift):
        self.shifts.append(shift)
        db.session.commit()

    def get_shifts(self, shift_type_name=None):
        """
        Filter shifts by the Name of the shift type (e.g., 'Morning')
        """
        if shift_type_name:
            return [shift for shift in self.shifts if shift.type.name == shift_type_name]
        return self.shifts

    def get_json(self):
        return {
            "id": self.id,
            "staff_id": self.staff_id,
            "admin_id": self.admin_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "shift_count": self.shift_count(),
            "shifts": [shift.get_json() for shift in self.shifts]
        }


