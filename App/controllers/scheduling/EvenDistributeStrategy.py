from App.models import Staff, Shift
from datetime import datetime
import random
from .SchedulingStrategy import SchedulingStrategy

class EvenDistributeStrategy(SchedulingStrategy):
    def generate_schedule(self, staff, shifts, start_date, end_date):
        """Ensure even distribution of hours and shifts among staff"""
        # Clear previous assignments
        for shift in shifts:
            shift.assigned_staff = []
        
        # Sort shifts by date and time
        shifts.sort(key=lambda x: x.start_time)
        
        # Track assignments
        staff_hours = {self._get_staff_id(s): 0 for s in staff}
        staff_shifts = {self._get_staff_id(s): 0 for s in staff}
        
        # Assign shifts using round-robin with balancing
        staff_queue = staff.copy()
        
        for shift in shifts:
            assigned = False
            attempts = 0
            
            while not assigned and attempts < len(staff_queue):
                # Get staff with least hours
                current_staff = min(staff_queue, key=lambda s: staff_hours[self._get_staff_id(s)])
                
                if self._can_take_shift(current_staff, shift):
                    shift.assigned_staff.append(current_staff)
                    staff_id = self._get_staff_id(current_staff)
                    staff_hours[staff_id] += self._get_shift_duration(shift)
                    staff_shifts[staff_id] += 1
                    assigned = True
                
                attempts += 1
                # Rotate staff for next attempt
                staff_queue = staff_queue[1:] + staff_queue[:1]
        
        # Calculate comprehensive metrics
        hours_values = [staff_hours[self._get_staff_id(s)] for s in staff]
        shifts_values = [staff_shifts[self._get_staff_id(s)] for s in staff]
        
        # Count staff with assignments
        staff_with_assignments = sum(1 for count in shifts_values if count > 0)
        
        summary = {
            'total_staff': len(staff),
            'staff_with_assignments': staff_with_assignments,
            'total_hours_assigned': sum(hours_values),
            'average_hours_per_staff': sum(hours_values) / len(hours_values) if hours_values else 0,
            'min_hours': min(hours_values) if hours_values else 0,
            'max_hours': max(hours_values) if hours_values else 0,
            'total_shifts_assigned': sum(shifts_values),
            'min_shifts': min(shifts_values) if shifts_values else 0,
            'max_shifts': max(shifts_values) if shifts_values else 0,
            'hours_std_dev': self._calculate_std_dev(hours_values),
            'shifts_std_dev': self._calculate_std_dev(shifts_values),
            'fairness_score': self._calculate_fairness_score(hours_values, shifts_values)
        }
        
        return {
            'strategy': "Even Distribution", 
            'score': summary['fairness_score'],
            'summary': summary,
            'schedule': shifts,
            'fairness_score': summary['fairness_score']
        }
    
    def _get_staff_id(self, staff):
        """Safely get staff ID"""
        if hasattr(staff, 'id'):
            return staff.id
        elif hasattr(staff, 'staff_id'):
            return staff.staff_id
        else:
            return id(staff)
    
    def _get_shift_duration(self, shift):
        """Calculate shift duration in hours"""
        if hasattr(shift, 'duration_hours'):
            return shift.duration_hours
        elif hasattr(shift, 'start_time') and hasattr(shift, 'end_time'):
            duration = shift.end_time - shift.start_time
            return duration.total_seconds() / 3600
        else:
            return 8.0
    
    def _can_take_shift(self, staff, shift):
        """Check if staff can take this shift"""
        return True
    
    def _calculate_fairness_score(self, hours, shifts):
        """Calculate fairness score (0-100)"""
        if not hours or max(hours) == 0:
            return 0
        
        # Hours fairness (70% weight)
        hours_range = max(hours) - min(hours)
        hours_score = 100 * (1 - (hours_range / max(hours))) if max(hours) > 0 else 0
        
        # Shifts fairness (30% weight)
        shifts_score = 100
        if shifts and max(shifts) > 0:
            shifts_range = max(shifts) - min(shifts)
            shifts_score = 100 * (1 - (shifts_range / max(shifts))) if max(shifts) > 0 else 0
        
        return (hours_score * 0.7) + (shifts_score * 0.3)
    
    def _calculate_std_dev(self, values):
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5