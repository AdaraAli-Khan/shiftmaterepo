# App/views/schedulingView.py
from flask import Blueprint, request, jsonify
from App.controllers.scheduling.schedule_client import schedule_client 
from App.controllers import get_user
from App.models import Schedule, Shift
from App.database import db
from datetime import datetime

scheduling_api = Blueprint('scheduling_api', __name__, url_prefix='/api')

@scheduling_api.route('/scheduling/auto-populate', methods=['POST'])
def auto_populate_schedule():
    """API endpoint for auto-populating schedules using strategies"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['admin_id', 'schedule_id', 'strategy_name', 'staff_ids', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Get admin user
        admin = get_user(data['admin_id'])
        if not admin or admin.role != 'admin':
            return jsonify({'success': False, 'error': 'Admin not found or invalid'}), 403
        
        # Verify schedule exists and belongs to admin
        schedule = Schedule.query.get(data['schedule_id'])
        if not schedule or schedule.created_by != admin.id:
            return jsonify({'success': False, 'error': 'Schedule not found or access denied'}), 404
        
        # Get staff objects from IDs
        staff_list = []
        for staff_id in data['staff_ids']:
            staff = get_user(staff_id)
            if staff and staff.role == 'staff':
                staff_list.append(staff)
        
        if not staff_list:
            return jsonify({'success': False, 'error': 'No valid staff members found'}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Validate date order
        if end_date < start_date:
            return jsonify({'success': False, 'error': 'End date cannot be before start date'}), 400
        
        # Create schedule using strategy
        result = schedule_client.auto_populate(
            admin_id=data['admin_id'],
            schedule_id=data['schedule_id'],
            strategy_name=data['strategy_name'],
            staff_list=staff_list,
            start_date=start_date,
            end_date=end_date,
            shifts_per_day=data.get('shifts_per_day', 2),
            shift_type=data.get('shift_type', 'mixed')
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'schedule_id': data['schedule_id'],  # use the schedule ID already passed
                'strategy_used': data['strategy_name'],
                'shifts_created': result.get('shifts_created', 0),
                'summary': result.get('summary', ''),
                'score': result.get('score', 0)
            }), 201
        else:
            return jsonify({'success': False, 'error': result.get('message', 'Auto-population failed')}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@scheduling_api.route('/scheduling/strategies', methods=['GET'])
def get_strategies():
    """Get available scheduling strategies"""
    strategies = schedule_client.get_available_strategies()
    return jsonify({'success': True, 'strategies': strategies}), 200

@scheduling_api.route('/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Get schedule details"""
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'success': False, 'error': 'Schedule not found'}), 404
    return jsonify({'success': True, 'schedule': schedule.get_json()}), 200

@scheduling_api.route('/schedules', methods=['GET'])
def get_all_schedules():
    """Get all schedules"""
    schedules = Schedule.query.all()
    return jsonify({'success': True, 'schedules': [s.get_json() for s in schedules]}), 200

@scheduling_api.route('/schedules', methods=['POST'])
def create_schedule():
    """Create a new schedule"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'created_by' not in data:
            return jsonify({'success': False, 'error': 'Name and created_by are required'}), 400
        
        # Verify admin user
        admin = get_user(data['created_by'])
        if not admin or admin.role != 'admin':
            return jsonify({'success': False, 'error': 'Only admins can create schedules'}), 403
        
        schedule = Schedule(name=data['name'], created_by=data['created_by'])
        db.session.add(schedule)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'schedule': schedule.get_json()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@scheduling_api.route('/schedules/<int:schedule_id>/shifts', methods=['GET'])
def get_schedule_shifts(schedule_id):
    """Get shifts for a specific schedule"""
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'success': False, 'error': 'Schedule not found'}), 404
    
    shifts = Shift.query.filter_by(schedule_id=schedule_id).all()
    return jsonify({
        'success': True, 
        'shifts': [shift.get_json() for shift in shifts]
    }), 200

@scheduling_api.route('/scheduling/compare', methods=['POST'])
def compare_strategies():
    """Compare all strategies for a set of staff and dates"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['admin_id', 'schedule_id', 'staff_ids', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Get admin user
        admin = get_user(data['admin_id'])
        if not admin or admin.role != 'admin':
            return jsonify({'success': False, 'error': 'Admin not found or invalid'}), 403
        
        # Verify schedule exists
        schedule = Schedule.query.get(data['schedule_id'])
        if not schedule:
            return jsonify({'success': False, 'error': 'Schedule not found'}), 404
        
        # Get staff objects from IDs
        staff_list = []
        for staff_id in data['staff_ids']:
            staff = get_user(staff_id)
            if staff and staff.role == 'staff':
                staff_list.append(staff)
        
        if not staff_list:
            return jsonify({'success': False, 'error': 'No valid staff members found'}), 400
        
        # Parse dates
        try:
            start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Compare strategies 
        comparison_results = {}
        best_strategy = None
        best_score = -1
        
        for strategy_name in ['even-distribute', 'minimize-days', 'preference-based']:
            try:
                result = schedule_client.auto_populate(
                    admin_id=data['admin_id'],
                    schedule_id=data['schedule_id'],
                    strategy_name=strategy_name,
                    staff_list=staff_list,
                    start_date=start_date,
                    end_date=end_date,
                    shifts_per_day=data.get('shifts_per_day', 2),
                    shift_type=data.get('shift_type', 'mixed')
                )
                
                if result['success']:
                    score = result.get('score', 0)
                    comparison_results[strategy_name] = {
                        'shifts_created': result['shifts_created'],
                        'summary': result['summary'],
                        'score': score
                    }
                    
                    # Track best strategy
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy_name
                else:
                    comparison_results[strategy_name] = {'error': result.get('message', 'Strategy failed')}
                    
            except Exception as e:
                comparison_results[strategy_name] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'comparison': comparison_results,
            'best_strategy': best_strategy
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400