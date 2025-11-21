from App.models import Staff, Shift
from datetime import datetime
import random
from .SchedulingStrategy import SchedulingStrategy


class EvenDistributeStrategy(SchedulingStrategy): # I used random shuffle to ensure fairness to schedule assignments
    
    def generate_schedule(self, staff, shifts, start_date, end_date):
        self._reset_assignments(staff, shifts)
        available_shifts = shifts.copy()
        staff_queue = staff.copy()
        random.shuffle(staff_queue) 
        
        while available_shifts and staff_queue:
            current_staff = staff_queue.pop(0)
            assigned_shift = self._find_suitable_shift(current_staff, available_shifts)
            
            if assigned_shift:
                self._assign_shift(current_staff, assigned_shift)
                available_shifts.remove(assigned_shift)
                
               
                max_hours = getattr(current_staff, 'max_hours_per_week', 40)
                assigned_shifts = getattr(current_staff, 'assigned_shifts', [])
                if (getattr(current_staff, 'total_hours', 0) < max_hours and
                    len(assigned_shifts) < len(shifts) // len(staff) + 2):
                    staff_queue.append(current_staff)
        
        return self._create_schedule_result(staff, shifts)

    def _find_suitable_shift(self, staff, shifts):
        for shift in shifts:
            assigned_count = len(getattr(shift, 'assigned_staff', []))
            required_staff = getattr(shift, 'required_staff', 1)
            if (self._is_staff_available(staff, shift) and
                self._has_required_skills(staff, shift) and
                assigned_count < required_staff):
                return shift
        return None

    def _is_staff_available(self, staff, shift):
        unavailable_days = getattr(staff, 'unavailable_days', [])
        return shift.start_time.weekday() not in unavailable_days

    def _has_required_skills(self, staff, shift):
        required_skills = getattr(shift, 'required_skills', [])
        staff_skills = getattr(staff, 'skills', [])
        return all(skill in staff_skills for skill in required_skills)

    def _assign_shift(self, staff, shift):
        assigned_staff = getattr(shift, 'assigned_staff', [])
        if staff not in assigned_staff:
            assigned_staff.append(staff)
            shift.assigned_staff = assigned_staff
        
        assigned_shifts = getattr(staff, 'assigned_shifts', [])
        if shift not in assigned_shifts:
            assigned_shifts.append(shift)
            staff.assigned_shifts = assigned_shifts
        
        staff.total_hours = getattr(staff, 'total_hours', 0) + getattr(shift, 'duration_hours', 8)
        staff.days_worked = getattr(staff, 'days_worked', 0) + 1

    def _reset_assignments(self, staff, shifts):
        for person in staff:
            person.assigned_shifts = []
            person.total_hours = 0
            person.days_worked = 0
        for shift in shifts:
            shift.assigned_staff = []

    def _create_schedule_result(self, staff, shifts):
        return {
            "strategy": "Even Distribution",
            "schedule": self._format_schedule(shifts),
            "summary": self._generate_summary(staff),
            "fairness_score": self._calculate_fairness_score(staff)
        }

    def _calculate_fairness_score(self, staff):
        if not staff:
            return 0.0
        hours = [getattr(person, 'total_hours', 0) for person in staff]
        avg_hours = sum(hours) / len(hours)
        variance = sum((h - avg_hours) ** 2 for h in hours) / len(hours)
        return max(0, 100 - (variance * 5))

    def _format_schedule(self, shifts):
        formatted = {}
        for shift in shifts:
            date_str = shift.start_time.strftime("%Y-%m-%d")
            if date_str not in formatted:
                formatted[date_str] = []
            formatted[date_str].append({
                "shift_id": getattr(shift, 'id', None),
                "shift_type": getattr(shift, 'shift_type', 'regular'),
                "staff": [getattr(person, 'username', str(person)) for person in getattr(shift, 'assigned_staff', [])],
                "time": f"{shift.start_time} - {shift.end_time}",
                "required_skills": getattr(shift, 'required_skills', [])
            })
        return formatted

    def _generate_summary(self, staff):
        total_staff = len(staff)
        total_hours = sum(getattr(person, 'total_hours', 0) for person in staff)
        hours_list = [getattr(person, 'total_hours', 0) for person in staff]
        return {
            "total_staff": total_staff,
            "total_hours_assigned": total_hours,
            "average_hours_per_staff": total_hours / total_staff if total_staff > 0 else 0,
            "min_hours": min(hours_list) if hours_list else 0,
            "max_hours": max(hours_list) if hours_list else 0,
            "total_shifts_assigned": sum(len(getattr(person, 'assigned_shifts', [])) for person in staff)
        }