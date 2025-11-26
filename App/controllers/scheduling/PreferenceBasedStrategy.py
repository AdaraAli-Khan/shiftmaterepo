# scheduling/PreferenceBasedStrategy.py
from .SchedulingStrategy import SchedulingStrategy
from App.controllers.preferences import get_preferences
from datetime import datetime

class PreferenceBasedStrategy(SchedulingStrategy):
    
    def generate_schedule(self, staff, shifts, start_date, end_date):
        self._reset_assignments(staff, shifts)
        
        # Load actual preferences for each staff member
        staff_preferences = {}
        for person in staff:
            try:
                prefs = get_preferences(person.id)
                staff_preferences[person] = prefs or {
                    'preferred_shift_types': [],
                    'unavailable_days': [],
                    'max_hours_per_week': 40,
                    'skills': []
                }
            except:
                # Fallback if preferences not found
                staff_preferences[person] = {
                    'preferred_shift_types': [],
                    'unavailable_days': [],
                    'max_hours_per_week': 40,
                    'skills': []
                }
        
        # Sort shifts by date and time
        sorted_shifts = sorted(shifts, key=lambda x: getattr(x, 'start_time', datetime.min))
        
        for shift in sorted_shifts:
            needed = getattr(shift, 'required_staff', 1) - len(getattr(shift, 'assigned_staff', []))
            if needed <= 0:
                continue
            
            # Get shift type and day
            shift_type = self._get_shift_type(shift)
            shift_day = shift.start_time.weekday() if hasattr(shift, 'start_time') else 0
            
            # Find best matching staff based on actual preferences
            candidates = []
            for person in staff:
                if not self._can_work_shift(person, shift, staff_preferences):
                    continue
                
                preference_score = self._calculate_preference_score(person, shift_day, shift_type, staff_preferences)
                current_hours = getattr(person, 'total_hours', 0)
                max_hours = staff_preferences[person].get('max_hours_per_week', 40)
                
                if current_hours < max_hours:
                    candidates.append((person, preference_score, current_hours))
            
            # Sort by preference score (descending) and current hours (ascending)
            candidates.sort(key=lambda x: (-x[1], x[2]))
            
            for person, score, hours in candidates[:needed]:
                self._assign_shift(person, shift)
        
        return self._create_schedule_result(staff, shifts)

    def _get_shift_type(self, shift):
        if not hasattr(shift, 'start_time'):
            return 'regular'
        
        hour = shift.start_time.hour
        if 6 <= hour < 14:
            return 'morning'
        elif 14 <= hour < 22:
            return 'evening'
        else:
            return 'night'

    def _can_work_shift(self, staff, shift, preferences):
        if not hasattr(shift, 'start_time'):
            return False
        
        prefs = preferences.get(staff, {})
        unavailable_days = prefs.get('unavailable_days', [])
        staff_skills = prefs.get('skills', [])
        required_skills = getattr(shift, 'required_skills', [])
        
        # Check if staff is available on this day
        if shift.start_time.weekday() in unavailable_days:
            return False
        
        # Check if staff has required skills
        if required_skills and not all(skill in staff_skills for skill in required_skills):
            return False
            
        return True

    def _calculate_preference_score(self, staff, day, shift_type, preferences):
        score = 0
        prefs = preferences.get(staff, {})
        preferred_shift_types = prefs.get('preferred_shift_types', [])
        unavailable_days = prefs.get('unavailable_days', [])
        
        # Bonus for preferred shift types
        if shift_type in preferred_shift_types:
            score += 3
            
        # Penalty for unavailable days (shouldn't happen due to _can_work_shift, but just in case)
        if day in unavailable_days:
            score -= 10
            
        return score

    def _assign_shift(self, staff, shift):
        if not hasattr(shift, 'assigned_staff'):
            shift.assigned_staff = []
        if not hasattr(staff, 'assigned_shifts'):
            staff.assigned_shifts = []
        if not hasattr(staff, 'total_hours'):
            staff.total_hours = 0
            
        shift.assigned_staff.append(staff)
        staff.assigned_shifts.append(shift)
        
        # Calculate shift duration
        if hasattr(shift, 'start_time') and hasattr(shift, 'end_time'):
            duration = (shift.end_time - shift.start_time).total_seconds() / 3600
        else:
            duration = getattr(shift, 'duration_hours', 8)
            
        staff.total_hours += duration

    def _create_schedule_result(self, staff, shifts):
        summary = self._generate_summary(staff)
        preference_score = self._calculate_overall_preference_score(staff)
        
        return {
            "strategy": "Preference Based",
            "schedule": self._format_schedule(shifts),
            "summary": summary,
            "preference_score": preference_score
        }

    def _calculate_overall_preference_score(self, staff):
        if not staff:
            return 0.0
        
        total_score = 0
        staff_count = 0
        
        for person in staff:
            assigned_shifts = getattr(person, 'assigned_shifts', [])
            if assigned_shifts:
                try:
                    prefs = get_preferences(person.id) or {}
                    preferred_types = prefs.get('preferred_shift_types', [])
                    
                    preferred_count = 0
                    for shift in assigned_shifts:
                        shift_type = self._get_shift_type(shift)
                        if shift_type in preferred_types:
                            preferred_count += 1
                    
                    if assigned_shifts:
                        total_score += (preferred_count / len(assigned_shifts)) * 100
                        staff_count += 1
                except:
                    continue
        
        return total_score / staff_count if staff_count > 0 else 0.0