# In App/controllers/scheduling/schedule_client.py
from .EvenDistributeStrategy import EvenDistributeStrategy
from .MinimizeStrategy import MinimizeDaysStrategy
from .PreferenceBasedStrategy import PreferenceBasedStrategy
from .DayNightDistributeStrategy import DayNightDistributeStrategy
from App.models import Shift
from App.database import db
from datetime import datetime, timedelta

class ScheduleClient:
    def __init__(self):
        self.strategies = {
            "even-distribute": EvenDistributeStrategy(),
            "minimize-days": MinimizeDaysStrategy(),
            "preference-based": PreferenceBasedStrategy(),
            "day-night-distribute": DayNightDistributeStrategy()
        }
    
    def generate_schedule(self, strategy_name, staff, shifts, start_date, end_date):
        """
        Generate schedule using the specified strategy
        """
        if strategy_name not in self.strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        strategy = self.strategies[strategy_name]
        return strategy.generate_schedule(staff, shifts, start_date, end_date)
    
    def auto_populate(self, admin_id, schedule_id, strategy_name, staff_list, start_date, end_date, shifts_per_day=2, shift_type='mixed'):
        """
        Auto-populate schedule with shifts using specified strategy
        Returns result dict for CLI to display
        """
        # Input validation
        if not staff_list:
            raise ValueError("Staff list cannot be empty")
        
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
        
        if shifts_per_day <= 0:
            raise ValueError("Shifts per day must be positive")
        
        try:
            # Clear existing shifts for this schedule
            deleted_count = self._clear_existing_shifts(schedule_id, start_date, end_date)
            
            # Generate shifts for the period
            shifts = self._generate_shifts_for_period(schedule_id, start_date, end_date, shifts_per_day, shift_type)
            
            # Use strategy to assign shifts
            result = self.generate_schedule(
                strategy_name=strategy_name,
                staff=staff_list,
                shifts=shifts,
                start_date=start_date,
                end_date=end_date
            )
            
            # Save shifts to database
            shifts_created = self._save_shifts_to_db(schedule_id, shifts)
            
            # Validate results
            summary = result.get('summary', {})
            self._validate_schedule_results(summary, len(staff_list))
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "shifts_created": shifts_created,
                "shifts_deleted": deleted_count,
                "score": result.get('score', 0),
                "summary": summary,  # Return raw summary for CLI to format
                "assignments": self._get_assignments_list(shifts),  # Add assignments for CLI display
                "strategy_used": strategy_name
            }
                
        except Exception as e:
            db.session.rollback()
            return {
                "success": False,
                "message": f"Failed to auto-generate schedule: {str(e)}"
            }

    def _get_assignments_list(self, shifts):
        """Get list of assignments for CLI display"""
        assignments = []
        for shift in shifts:
            if hasattr(shift, 'assigned_staff') and shift.assigned_staff:
                for staff in shift.assigned_staff:
                    staff_id = getattr(staff, 'id', 'Unknown')
                    assignments.append({
                        'staff_id': staff_id,
                        'start_time': shift.start_time,
                        'end_time': shift.end_time
                    })
        return assignments

    def _validate_schedule_results(self, summary, staff_count):
        """Validate that the schedule results are reasonable"""
        if not summary:
            return
        
        # Check for extreme imbalances
        if summary.get('max_hours', 0) - summary.get('min_hours', 0) > 20:
            raise ValueError("Schedule too unbalanced - hour difference exceeds 20 hours")
        
        # Check if all staff got reasonable assignments
        if summary.get('total_shifts_assigned', 0) < staff_count:
            raise ValueError("Not enough shifts assigned - some staff may have no shifts")
        
        # Check for reasonable distribution
        if summary.get('max_hours', 0) > summary.get('average_hours_per_staff', 0) * 1.5:
            raise ValueError("Schedule distribution too uneven")

    def _clear_existing_shifts(self, schedule_id, start_date, end_date):
        """Clear existing shifts in the date range"""
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        shifts = Shift.query.filter(
            Shift.schedule_id == schedule_id,
            Shift.start_time >= start_datetime,
            Shift.start_time <= end_datetime
        ).all()
        
        for shift in shifts:
            db.session.delete(shift)
        db.session.commit()
        
        return len(shifts)

    def _save_shifts_to_db(self, schedule_id, shifts):
        """Save assigned shifts to database and return count"""
        shifts_created = 0
        
        for shift in shifts:
            if hasattr(shift, 'assigned_staff') and shift.assigned_staff:
                for staff in shift.assigned_staff:
                    try:
                        # Get staff ID safely
                        staff_id = getattr(staff, 'id', None)
                        if staff_id is None:
                            continue
                        
                        new_shift = Shift(
                            schedule_id=schedule_id,
                            staff_id=staff_id,
                            start_time=shift.start_time,
                            end_time=shift.end_time
                        )
                        db.session.add(new_shift)
                        shifts_created += 1
                    except Exception as e:
                        # Log error but don't print - let CLI handle display
                        continue
        
        try:
            db.session.commit()
            return shifts_created
        except Exception as e:
            db.session.rollback()
            raise
        
    def _generate_shifts_for_period(self, schedule_id, start_date, end_date, shifts_per_day, shift_type):
        """Generate shift objects for the given period"""
        shifts = []
        current_date = start_date
        
        while current_date <= end_date:
            for shift_num in range(shifts_per_day):
                shift_times = self._get_shift_times(current_date, shift_num, shifts_per_day, shift_type)
                
                class MockShift:
                    def __init__(self, start_time, end_time):
                        self.start_time = start_time
                        self.end_time = end_time
                        self.assigned_staff = []
                        self.required_staff = 1
                        self.duration_hours = (end_time - start_time).total_seconds() / 3600
                        self.required_skills = []
                        self.shift_type = shift_type
                
                shift = MockShift(shift_times['start'], shift_times['end'])
                shifts.append(shift)
            
            current_date += timedelta(days=1)
        
        return shifts
    
    def _get_shift_times(self, date, shift_num, shifts_per_day, shift_type):
        """Generate shift times based on shift type"""
        base_date = datetime.combine(date, datetime.min.time())
        
        if shift_type == 'day':
            start_hour = 8 + shift_num
            return {
                'start': base_date.replace(hour=start_hour),
                'end': base_date.replace(hour=start_hour + 8)
            }
        elif shift_type == 'night':
            start_hour = 22 + shift_num
            end_date = date + timedelta(days=1)
            return {
                'start': base_date.replace(hour=start_hour),
                'end': datetime.combine(end_date, datetime.min.time()).replace(hour=(start_hour + 8) % 24)
            }
        else:  # mixed
            if shift_num == 0:  # Morning
                return {
                    'start': base_date.replace(hour=8),
                    'end': base_date.replace(hour=16)
                }
            else:  # Evening
                return {
                    'start': base_date.replace(hour=16),
                    'end': base_date.replace(hour=23, minute=59)
                }
    
    def get_available_strategies(self):
        return list(self.strategies.keys())

# Global instance
schedule_client = ScheduleClient()