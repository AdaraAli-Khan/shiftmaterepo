# App/database.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()


def get_migrate(app):
    return Migrate(app, db)


def init_db(app):
    """
    Initialize SQLAlchemy with the app and ensure tables exist.
    Called from create_app() in main.py.
    """
    db.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        from App import models  # ensure User and others are imported
        db.create_all()


def create_db(app=None):
    """
    Helper used by tests (and optionally scripts) to create all tables.

    Signature kept compatible with:
        from App.database import db, create_db
    so tests can call either:
        create_db(app)
    or, when an app context is already pushed:
        create_db()
    """
    from flask import current_app

    if app is None:
        app = current_app

    with app.app_context():
        from App import models  # ensure models are registered
        db.create_all()
