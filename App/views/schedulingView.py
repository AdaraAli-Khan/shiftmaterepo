# App/views/api/scheduling_views.py
from flask import Blueprint, request, jsonify
from App.controllers.scheduling.schedule_client import schedule_client 
from App.controllers.user import get_user
from App.controllers.admin import _ensure_admin
from datetime import datetime

scheduling_api = Blueprint('scheduling_api', __name__)

@scheduling_api.route('/api/scheduling/auto-populate', methods=['POST'])
def auto_populate_schedule():
    """API endpoint for auto-populating schedules using strategies"""
    try:
        data = request.get_json()
        
        # Validate admin
        _ensure_admin(data.get('admin_id'))
        
        # Get staff objects from IDs
        staff_list = []
        for staff_id in data['staff_ids']:
            staff = get_user(staff_id)
            if staff and hasattr(staff, 'role') and staff.role == 'staff':
                staff_list.append(staff)
        
        if not staff_list:
            return jsonify({'success': False, 'error': 'No valid staff members found'}), 400
        
        # Create schedule using strategy
        result = schedule_client.auto_populate(
            admin_id=data['admin_id'],
            strategy_name=data['strategy_name'],
            staff_list=staff_list,  # Pass staff objects, not IDs
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            shifts_per_day=data.get('shifts_per_day', 2)
        )
        
        return jsonify({
            'success': True,
            'schedule_id': result['schedule'].id,
            'strategy_used': data['strategy_name'],
            'summary': result['summary'],
            'score': result['score']
        }), 201
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@scheduling_api.route('/api/scheduling/strategies', methods=['GET'])
def get_strategies():
    """Get available scheduling strategies"""
    strategies = schedule_client.get_available_strategies()
    return jsonify({'success': True, 'strategies': strategies}), 200

@scheduling_api.route('/api/schedules/<int:schedule_id>', methods=['GET'])
def get_schedule(schedule_id):
    """Get schedule details"""
    from App.models import Schedule
    schedule = Schedule.query.get(schedule_id)
    if not schedule:
        return jsonify({'success': False, 'error': 'Schedule not found'}), 404
    return jsonify({'success': True, 'schedule': schedule.get_json()}), 200

@scheduling_api.route('/api/schedules', methods=['GET'])
def get_all_schedules():
    """Get all schedules"""
    from App.models import Schedule
    schedules = Schedule.query.all()
    return jsonify({'success': True, 'schedules': [s.get_json() for s in schedules]}), 200


@scheduling_api.route('/api/scheduling/compare', methods=['POST'])
def compare_strategies():
    """Compare all strategies for a set of staff and dates"""
    try:
        data = request.get_json()
        
        # Validate admin
        _ensure_admin(data.get('admin_id'))
        
        # Get staff objects from IDs
        staff_list = []
        for staff_id in data['staff_ids']:
            staff = get_user(staff_id)
            if staff and hasattr(staff, 'role') and staff.role == 'staff':
                staff_list.append(staff)
        
        if not staff_list:
            return jsonify({'success': False, 'error': 'No valid staff members found'}), 400
        
        # Compare strategies
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        comparison_results = {}
        best_strategy = None
        best_score = -1
        
        for strategy_name in ['even_distribute', 'minimize_days', 'shift_type_optimize']:
            try:
                result = schedule_client.auto_populate(
                    admin_id=data['admin_id'],
                    strategy_name=strategy_name,
                    staff_list=staff_list,
                    start_date=start_date,
                    end_date=end_date,
                    shifts_per_day=data.get('shifts_per_day', 2)
                )
                
                score = result.get('score', 0)
                comparison_results[strategy_name] = {
                    'schedule_id': result['schedule'].id,
                    'summary': result['summary'],
                    'score': score
                }
                
                # Track best strategy
                if score > best_score:
                    best_score = score
                    best_strategy = strategy_name
                    
            except Exception as e:
                comparison_results[strategy_name] = {'error': str(e)}
        
        return jsonify({
            'success': True,
            'comparison': comparison_results,
            'best_strategy': best_strategy
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
