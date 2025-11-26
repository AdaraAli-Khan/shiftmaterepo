# scheduling/DayNightDistributeStrategy.py
from .SchedulingStrategy import SchedulingStrategy
from App.controllers.preferences import get_preferences
from datetime import datetime

class DayNightDistributeStrategy(SchedulingStrategy):
    
    def generate_schedule(self, staff, shifts, start_date, end_date):
        self._reset_assignments(staff, shifts)
        
        # Separate day and night shifts
        day_shifts = []
        night_shifts = []
        
        for shift in shifts:
            shift_type = self._get_shift_type(shift)
            if shift_type in ['morning', 'evening']:
                day_shifts.append(shift)
            else:  # night
                night_shifts.append(shift)
        
        # Group staff by preference for day/night shifts
        day_staff = []
        night_staff = []
        neutral_staff = []
        
        for person in staff:
            try:
                prefs = get_preferences(person.id) or {}
                preferred_types = prefs.get('preferred_shift_types', [])
                
                day_pref = any(t in ['morning', 'evening'] for t in preferred_types)
                night_pref = 'night' in preferred_types
                
                if day_pref and not night_pref:
                    day_staff.append(person)
                elif night_pref and not day_pref:
                    night_staff.append(person)
                else:
                    neutral_staff.append(person)
            except:
                neutral_staff.append(person)
        
        # Assign day shifts
        for shift in day_shifts:
            needed = getattr(shift, 'required_staff', 1) - len(getattr(shift, 'assigned_staff', []))
            if needed <= 0:
                continue
            
            # Try day-preferring staff first, then neutral
            candidates = day_staff + neutral_staff
            candidates = [s for s in candidates if self._can_work_shift(s, shift)]
            
            # Sort by current hours (ascending)
            candidates.sort(key=lambda x: getattr(x, 'total_hours', 0))
            
            for person in candidates[:needed]:
                if self._assign_if_available(person, shift):
                    if person in neutral_staff:
                        neutral_staff.remove(person)
        
        # Assign night shifts
        for shift in night_shifts:
            needed = getattr(shift, 'required_staff', 1) - len(getattr(shift, 'assigned_staff', []))
            if needed <= 0:
                continue
            
            # Try night-preferring staff first, then neutral
            candidates = night_staff + neutral_staff
            candidates = [s for s in candidates if self._can_work_shift(s, shift)]
            
            # Sort by current hours (ascending)
            candidates.sort(key=lambda x: getattr(x, 'total_hours', 0))
            
            for person in candidates[:needed]:
                if self._assign_if_available(person, shift):
                    if person in neutral_staff:
                        neutral_staff.remove(person)
        
        return self._create_schedule_result(staff, shifts, len(day_staff), len(night_staff))

    def _get_shift_type(self, shift):
        if not hasattr(shift, 'start_time'):
            return 'regular'
        
        hour = shift.start_time.hour
        if 6 <= hour < 18:  # 6am to 6pm considered day
            return 'day' if hour < 14 else 'evening'
        else:
            return 'night'

    def _can_work_shift(self, staff, shift):
        if not hasattr(shift, 'start_time'):
            return False
            
        try:
            prefs = get_preferences(staff.id) or {}
            unavailable_days = prefs.get('unavailable_days', [])
            staff_skills = prefs.get('skills', [])
        except:
            unavailable_days = []
            staff_skills = []
            
        required_skills = getattr(shift, 'required_skills', [])
        
        return (shift.start_time.weekday() not in unavailable_days and
                all(skill in staff_skills for skill in required_skills))

    def _assign_if_available(self, staff, shift):
        max_hours = 40
        try:
            prefs = get_preferences(staff.id) or {}
            max_hours = prefs.get('max_hours_per_week', 40)
        except:
            pass
            
        current_hours = getattr(staff, 'total_hours', 0)
        shift_hours = self._get_shift_duration(shift)
        
        if current_hours + shift_hours <= max_hours:
            self._assign_shift(staff, shift)
            return True
        return False

    def _get_shift_duration(self, shift):
        if hasattr(shift, 'start_time') and hasattr(shift, 'end_time'):
            return (shift.end_time - shift.start_time).total_seconds() / 3600
        return getattr(shift, 'duration_hours', 8)

    def _assign_shift(self, staff, shift):
        if not hasattr(shift, 'assigned_staff'):
            shift.assigned_staff = []
        if not hasattr(staff, 'assigned_shifts'):
            staff.assigned_shifts = []
        if not hasattr(staff, 'total_hours'):
            staff.total_hours = 0
            
        shift.assigned_staff.append(staff)
        staff.assigned_shifts.append(shift)
        staff.total_hours += self._get_shift_duration(shift)

    def _create_schedule_result(self, staff, shifts, day_staff_count, night_staff_count):
        summary = self._generate_summary(staff)
        
        day_shifts = len([s for s in shifts if self._get_shift_type(s) in ['day', 'evening'] and hasattr(s, 'assigned_staff') and s.assigned_staff])
        night_shifts = len([s for s in shifts if self._get_shift_type(s) == 'night' and hasattr(s, 'assigned_staff') and s.assigned_staff])
        
        summary.update({
            "day_staff_count": day_staff_count,
            "night_staff_count": night_staff_count,
            "day_shifts_assigned": day_shifts,
            "night_shifts_assigned": night_shifts
        })
        
        return {
            "strategy": "Day/Night Distribution",
            "schedule": self._format_schedule(shifts),
            "summary": summary,
            "distribution_score": self._calculate_distribution_score(day_shifts, night_shifts, day_staff_count, night_staff_count)
        }

    def _calculate_distribution_score(self, day_shifts, night_shifts, day_staff, night_staff):
        if day_shifts + night_shifts == 0:
            return 0.0
            
        total_staff = day_staff + night_staff
        if total_staff == 0:
            return 0.0
            
        ideal_day_ratio = day_staff / total_staff
        actual_day_ratio = day_shifts / (day_shifts + night_shifts) if (day_shifts + night_shifts) > 0 else 0
        
        # Score based on how close actual distribution is to ideal
        deviation = abs(ideal_day_ratio - actual_day_ratio)
        return max(0, 100 - (deviation * 200))