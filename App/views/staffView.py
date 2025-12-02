# app/views/staff_views.py
from flask import Blueprint, jsonify, request
from App.controllers import staff, auth
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError

staff_views = Blueprint('staff_views', __name__, template_folder='../templates')

#Based on the controllers in App/controllers/staff.py, staff can do the following actions:
# 1. View combined roster
# 2. Clock in 
# 3. Clock out
# 4. View specific shift details

staff_views = Blueprint('staff_views', __name__, template_folder='../templates')

# Staff view roster route
@staff_views.route('/staff/roster', methods=['GET'])
@jwt_required()
def view_roster():
    try:
        staff_id = get_jwt_identity()  # get the user id stored in JWT
        # staffData = staff.get_user(staff_id).get_json()  # Fetch staff data
        roster = staff.get_combined_roster(staff_id)  # staff.get_combined_roster should return the json data of the roseter
        return jsonify(roster), 200
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500

@staff_views.route('/staff/shift', methods=['GET'])
@jwt_required()
def view_shift():
    try:
        data = request.get_json()
        shift_id = data.get("shiftID")  # gets the shiftID from the request
        shift = staff.get_shift(shift_id)  # Call controller
        if not shift:
            return jsonify({"error": "Shift not found"}), 404
        return jsonify(shift.get_json()), 200
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500

# Staff Clock in endpoint
@staff_views.route('/staff/clock_in', methods=['POST'])
@jwt_required()
def clockIn():
    try:
        staff_id = int(get_jwt_identity())  # Ensure it's an integer

        data = request.get_json()
        if not data or 'shiftID' not in data:
            return jsonify({"error": "shiftID is required"}), 400

        shift_id = int(data['shiftID'])
        shiftOBJ = staff.clock_in(staff_id, shift_id)

        if not shiftOBJ:
            return jsonify({"error": "Shift not found or clock-in failed"}), 404

        return jsonify(shiftOBJ.get_json()), 200

    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        # Catch any other unexpected error
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


# Staff Clock in endpoint
@staff_views.route('/staff/clock_out', methods=['POST'])
@jwt_required()
def clock_out():
    try:
        staff_id = int(get_jwt_identity())  # Ensure it's an integer

        data = request.get_json()
        if not data or 'shiftID' not in data:
            return jsonify({"error": "shiftID is required"}), 400

        shift_id = int(data['shiftID'])
        shiftOBJ = staff.clock_out(staff_id, shift_id)

        if not shiftOBJ:
            return jsonify({"error": "Shift not found or clock-out failed"}), 404

        return jsonify(shiftOBJ.get_json()), 200

    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
    except SQLAlchemyError:
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500