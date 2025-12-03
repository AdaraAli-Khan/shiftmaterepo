  
    # App/database.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

def get_migrate(app):
    return Migrate(app, db)

def init_db(app):
    db.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        # Import models so SQLAlchemy knows them (User, etc.)
        from App import models
        db.create_all()
