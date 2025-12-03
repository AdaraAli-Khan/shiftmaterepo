from flask import Blueprint, render_template, jsonify, request, flash, send_from_directory, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies


from.index import index_views

from App.controllers import (
    login,

)

auth_views = Blueprint('auth_views', __name__, template_folder='../templates')




'''
Page/Action Routes
'''    

@auth_views.route('/identify', methods=['GET'])
@jwt_required()
def identify_page():
    return render_template('message.html', title="Identify", message=f"You are logged in as {current_user.id} - {current_user.username}")
    
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_jwt_extended import jwt_required, current_user, unset_jwt_cookies, set_access_cookies

from .index import index_views
from App.controllers import login


@auth_views.route('/login', methods=['POST'])
def login_action():
    # Accept both JSON and form-encoded
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form or {}

    username = data.get('username')
    password = data.get('password')

    # Decide if the client wants JSON (Postman / JS) or HTML (browser form)
    wants_json = request.is_json or (
        request.accept_mimetypes['application/json']
        >= request.accept_mimetypes['text/html']
    )

    # Basic validation
    if not username or not password:
        if wants_json:
            return jsonify(message='Username and password required'), 400
        flash('Username and password required')
        next_url = url_for('index_views.index_page')
        return redirect(next_url)

    token = login(username, password)

    if not token:
        if wants_json:
            return jsonify(message='Bad username or password given'), 401
        flash('Bad username or password given')
        next_url = url_for('index_views.index_page')
        return redirect(next_url)

    # Successful login
    if wants_json:
        # API-style response (for Postman / JS)
        response = jsonify(message='Login successful', access_token=token)
        set_access_cookies(response, token)
        return response

    # Browser-style response (redirect + flash)
    flash('Login Successful')
    next_url = url_for('index_views.index_page')
    response = redirect(next_url)
    set_access_cookies(response, token)
    return response

# @auth_views.route('/login', methods=['POST'])
# def login_action():
#     # Accept JSON OR form-encoded
#     if request.is_json:
#         data = request.get_json(silent=True) or {}
#     else:
#         data = request.form  # from <form> submit

#     username = data.get('username')
#     password = data.get('password')

#     token = login(username, password)

#     # redirect target: never None
#     next_url = request.referrer or url_for('index_views.index')

#     if not token:
#         flash('Bad username or password given')
#         return redirect(next_url)

#     flash('Login Successful')
#     response = redirect(next_url)
#     set_access_cookies(response, token)
#     return response



@auth_views.route('/logout', methods=['GET'])
def logout_action():
    response = redirect(request.referrer) 
    flash("Logged Out!")
    unset_jwt_cookies(response)
    return response

'''
API Routes
'''

@auth_views.route('/api/login', methods=['POST'])
def user_login_api():
  data = request.json
  token = login(data['username'], data['password'])
  if not token:
    return jsonify(message='bad username or password given'), 401
  response = jsonify(access_token=token) 
  set_access_cookies(response, token)
  return response

@auth_views.route('/api/identify', methods=['GET'])
@jwt_required()
def identify_user():
    return jsonify({'message': f"username: {current_user.username}, id : {current_user.id}"})

@auth_views.route('/api/logout', methods=['GET'])
def logout_api():
    response = jsonify(message="Logged Out!")
    unset_jwt_cookies(response)
    return response