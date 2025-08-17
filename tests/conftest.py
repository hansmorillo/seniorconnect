# conftest.py
import pytest
import uuid
from flask import url_for
from app import create_app
from extensions import db
from models.user import User
from models.notifications import Notification

@pytest.fixture
def app():
    """Create application for testing"""
    # Create test configuration that properly overrides the database
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
        "SECRET_KEY": "test-secret-key"
    }
    
    app = create_app(test_config=test_config)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test runner"""
    return app.test_cli_runner()

@pytest.fixture
def test_user(app):
    """Create a test user"""
    with app.app_context():
        from extensions import bcrypt
        user = User(
            id=str(uuid.uuid4()),
            display_name="Test User",
            email="user1@test.com",
            phone_number="1234567890",
            password_hash=bcrypt.generate_password_hash('password').decode('utf-8')
        )
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def test_user2(app):
    """Create a second test user"""
    with app.app_context():
        from extensions import bcrypt
        user2 = User(
            id=str(uuid.uuid4()),
            display_name="Test User 2",
            email="user2@test.com",
            phone_number="0987654321",
            password_hash=bcrypt.generate_password_hash('password2').decode('utf-8')
        )
        db.session.add(user2)
        db.session.commit()
        return user2

class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, email='user1@test.com', password='password'):
        """Login helper method"""
        return self._client.post(
            url_for('auth.login'),
            data={'email': email, 'password': password},
            follow_redirects=True
        )

    def logout(self):
        """Logout helper method"""
        return self._client.get(url_for('auth.logout'), follow_redirects=True)

@pytest.fixture
def auth(client):
    """Authentication helper fixture"""
    return AuthActions(client)