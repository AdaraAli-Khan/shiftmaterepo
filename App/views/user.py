from flask import Blueprint, render_template, jsonify, request, send_from_directory, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user as jwt_current_user

from.index import index_views

from App.controllers import (
    create_user,
    get_all_users,
    get_all_users_json,
)

user_views = Blueprint('user_views', __name__, template_folder='../templates')

@user_views.route('/users', methods=['GET'])
def get_user_page():
    users = get_all_users()
    return render_template('users.html', users=users)

@user_views.route('/users', methods=['POST'])
def create_user_action():
    data = request.form
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        flash("Username and password are required!", "error")
        return redirect(url_for('user_views.get_user_page'))

    try:
        create_user(username, password)
        flash(f"User {username} created!", "success")
    except Exception as e:
        flash(f"Error creating user: {str(e)}", "error")

    return redirect(url_for('user_views.get_user_page'))

@user_views.route('/api/users', methods=['GET'])
def get_users_action():
    users = get_all_users_json()
    return jsonify(users)

@user_views.route('/api/users', methods=['POST'])
@jwt_required()  # Protect this endpoint
def create_user_endpoint():
    data = request.get_json()

    # Validation
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Username and password are required"}), 400

    try:
        user = create_user(data['username'], data['password'], data.get('role', 'user'))
        return jsonify({"message": f"User {user.username} created with id {user.id}"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@user_views.route('/static/users', methods=['GET'])
def static_user_page():
  return send_from_directory('static', 'static-user.html')