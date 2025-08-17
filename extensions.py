# extensions.py - CLEAN FIXED VERSION
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import os

# Initialize core extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Initialize limiter as None - will be set in init_extensions
limiter = None

def get_user_id():
    """
    Custom key function for user-based rate limiting
    Uses user ID for logged-in users, IP for anonymous users
    """
    try:
        # Import inside function to avoid circular imports
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            return f"user:{current_user.id}"
        return f"ip:{get_remote_address()}"
    except:
        return f"ip:{get_remote_address()}"

def get_user_and_ip():
    """
    Combination key function for stricter rate limiting
    """
    try:
        from flask_login import current_user
        user_part = f"user:{current_user.id}" if current_user and current_user.is_authenticated else "anonymous"
        ip_part = f"ip:{get_remote_address()}"
        return f"{user_part}:{ip_part}"
    except:
        return f"anonymous:ip:{get_remote_address()}"

def init_extensions(app):
    """Initialize all extensions including rate limiter"""
    global limiter
    
    # Initialize core extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Initialize rate limiter
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        # Test Redis connection
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        
        limiter = Limiter(
            app=app,
            key_func=get_user_id,
            storage_uri=redis_url,
            default_limits=[
                "1000 per day", 
                "200 per hour", 
                "50 per 10 minutes"
            ],
            headers_enabled=True,
            strategy="fixed-window"
        )
        print("✅ Rate Limiter: Using Redis storage backend")
        
    except Exception as e:
        limiter = Limiter(
            app=app,
            key_func=get_user_id,
            default_limits=[
                "1000 per day",
                "200 per hour", 
                "50 per 10 minutes"
            ],
            headers_enabled=True,
            strategy="fixed-window"
        )
        print(f"⚠️  Rate Limiter: Using memory storage (Redis unavailable: {str(e)[:50]}...)")
    
    return limiter