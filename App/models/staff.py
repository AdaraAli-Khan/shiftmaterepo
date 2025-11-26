from App.database import db
from .user import User


class Staff(User):
    id = db.Column(db.Integer, db.ForeignKey("user.id"), primary_key=True)

    # Optional one-to-one relation to a Preferences row
    preferences = db.relationship(
        "Preferences",
        uselist=False,
        backref=db.backref("staff", lazy=True),
        foreign_keys="Preferences.staff_id",
        cascade="all, delete-orphan",
    )

    __mapper_args__ = {
        "polymorphic_identity": "staff",
    }

    def __init__(self, username, password, **kwargs):
        # allow passing through additional preference-related fields
        super().__init__(username, password, "staff")

    # Convenience accessors used by scheduling strategies (they expect
    # attributes on staff objects rather than a separate Preferences object)
    @property
    def preferred_shift_types(self):
        if self.preferences and self.preferences.preferred_shift_types:
            return self.preferences.preferred_shift_types
        return ["regular"]

    @property
    def unavailable_days(self):
        if self.preferences and self.preferences.unavailable_days is not None:
            return self.preferences.unavailable_days
        return []

    @property
    def skills(self):
        if self.preferences and self.preferences.skills:
            return self.preferences.skills
        return []

    @property
    def max_hours_per_week(self):
        if self.preferences and self.preferences.max_hours_per_week is not None:
            return self.preferences.max_hours_per_week
        return 40
