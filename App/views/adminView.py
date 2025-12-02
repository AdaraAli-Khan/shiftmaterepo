# app/views/staff_views.py
from flask import Blueprint, jsonify, request
from datetime import datetime
from App.controllers import staff, auth, admin
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

admin_view = Blueprint('admin_view', __name__, template_folder='../templates',url_prefix='/admin')

# Admin authentication decorator
# def admin_required(fn):
#     @jwt_required()
#     def wrapper(*args, **kwargs):
#         user_id = get_jwt_identity()
#         user = auth.get_user(user_id)
#         if not user or not user.is_admin:
#             return jsonify({"error": "Admin access required"}), 403
#         return fn(*args, **kwargs)
#     return wrapper
# Based on the controllers in App/controllers/admin.py, admins can do the following actions:
# 1. Create Schedule
# 2. Get Schedule Report

@admin_view.route('/createSchedule', methods=['POST'])
@jwt_required()
def createSchedule():
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        scheduleName = data.get("scheduleName") # gets the scheduleName from the request body
        schedule = admin.create_schedule(admin_id, scheduleName)  # Call controller method
        
        return jsonify(schedule.get_json()), 200 # Return the created schedule as JSON
    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500

@admin_view.route('/createShift', methods=['POST'])
@jwt_required()
def createShift():
    try:
        admin_id = get_jwt_identity()
        data = request.get_json()
        scheduleID = data.get("scheduleID") # gets the scheduleID from the request body
        staffID = data.get("staffID") # gets the staffID from the request body
        startTime = data.get("start_time") # gets the startTime from the request body
        endTime = data.get("end_time") # gets the endTime from the request body

    # Try ISO first, fallback to "YYYY-MM-DD HH:MM:SS"
        try:
            start_time = datetime.fromisoformat(startTime)
            end_time = datetime.fromisoformat(endTime)
        except ValueError:
            start_time = datetime.strptime(startTime, "%Y-%m-%d %H:%M:%S")
            end_time = datetime.strptime(endTime, "%Y-%m-%d %H:%M:%S")

        shift = admin.schedule_shift(admin_id, staffID, scheduleID, start_time, end_time)  # Call controller method
        print("Debug: Created shift in view:", shift.get_json())
        
        return jsonify(shift.get_json()), 200 # Return the created shift as JSON
    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500

@admin_view.route('/shiftReport', methods=['GET'])
@jwt_required()
def shiftReport():
    try:
        admin_id = get_jwt_identity()
        report = admin.get_shift_report(admin_id)  # Call controller method
        return jsonify(report), 200
    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500