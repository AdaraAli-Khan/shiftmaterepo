# App/controllers/schedule_client.py
from App.models import Schedule, Shift
from App.database import db
from App.controllers.scheduling import Scheduler
from datetime import datetime, date, timedelta

class ScheduleClient:
    def __init__(self):
        self.scheduler = Scheduler()
    
    def auto_populate(self, admin_id, strategy_name, staff_list, start_date, end_date, shifts_per_day=2):
        """
        Auto-populate schedule using different strategies
        """
        try:
            # Create shifts for the period
            shifts = self._generate_shifts(start_date, end_date, shifts_per_day)
            
            # Use strategy to assign staff
            result = self.scheduler.generate_schedule(strategy_name, staff_list, shifts, start_date, end_date)
            
            # Create and save schedule
            schedule = self._create_schedule(admin_id, strategy_name, start_date, end_date)
            self._save_assigned_shifts(result['schedule'], schedule.id, staff_list)
            
            return {
                "schedule": schedule,
                "summary": result['summary'],
                "score": result.get('fairness_score', result.get('efficiency_score', result.get('preference_score', 0)))
            }
        except Exception as e:
            raise Exception(f"Failed to auto-populate schedule: {str(e)}")
    
    def _generate_shifts(self, start_date, end_date, shifts_per_day):
        """Generate shift templates for the period"""
        shifts = []
        shift_id = 1
        current_date = start_date
        
        shift_times = [
            ("morning", 8, 16),
            ("evening", 16, 23)  
        ]
        
        while current_date <= end_date:
            for i in range(shifts_per_day):
                shift_type, start_hour, end_hour = shift_times[i % len(shift_times)]
                
                # Create shift template object
                shift_template = type('ShiftTemplate', (), {})()
                shift_template.id = shift_id
                shift_template.start_time = datetime.combine(current_date, datetime.min.time().replace(hour=start_hour))
                # Handle day boundary for evening shift
                if end_hour == 23:
                    shift_template.end_time = datetime.combine(current_date, datetime.min.time().replace(hour=end_hour, minute=59))
                else:
                    shift_template.end_time = datetime.combine(current_date, datetime.min.time().replace(hour=end_hour))
                shift_template.shift_type = shift_type
                shift_template.required_staff = 1
                shift_template.duration_hours = 8
                shift_template.required_skills = []
                
                shifts.append(shift_template)
                shift_id += 1
            
            current_date += timedelta(days=1)
        
        return shifts
    
    def _create_schedule(self, admin_id, strategy_name, start_date, end_date):
        """Create a new schedule in database"""
        schedule = Schedule(
            name=f"{strategy_name} Schedule {start_date} to {end_date}",
            created_by=admin_id
        )
        db.session.add(schedule)
        db.session.commit()
        return schedule
    
    def _save_assigned_shifts(self, schedule_data, schedule_id, staff_list):
        """Save assigned shifts to database"""
        if not isinstance(schedule_data, dict):
            return
            
        try:
            for date_str, shifts in schedule_data.items():
                if not isinstance(shifts, list):
                    continue
                    
                for shift_info in shifts:
                    # Skip if shift_info doesn't have required datetime objects
                    start_time = shift_info.get('start_time')
                    end_time = shift_info.get('end_time')
                    
                    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
                        continue
                    
                    # Assign to first available staff for this shift
                    staff_list_for_shift = shift_info.get('staff', [])
                    for staff_name in staff_list_for_shift:
                        # Find staff by username
                        for staff in staff_list:
                            if getattr(staff, 'username', f'staff_{staff.id}') == staff_name:
                                shift = Shift(
                                    staff_id=staff.id,
                                    schedule_id=schedule_id,
                                    start_time=start_time,
                                    end_time=end_time,
                                    shift_type=shift_info.get('shift_type', 'regular')
                                )
                                db.session.add(shift)
                                break
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            
    
    def get_available_strategies(self):
        """Get list of available strategies"""
        return self.scheduler.get_available_strategies()

# Create global instance
schedule_client = ScheduleClient()