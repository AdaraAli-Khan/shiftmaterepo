import pytest
from App.main import create_app
from App.database import db, create_db


@pytest.fixture
def client():
    """Create a test client for API testing"""
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:'})
    
    with app.app_context():
        create_db()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def init_database():
    """Initialize a fresh database for each test"""
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()
