# =============================================================================
# RATE LIMITER IMPLEMENTATION FOR FLASK APP
# OWASP A05:2021 – Security Misconfiguration Protection
# =============================================================================

# requirements.txt addition:
# Flask-Limiter==3.12

# 1. RATE LIMITER CONFIGURATION (rate_limiter.py)
# =============================================================================

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, current_user
import redis
import os
from functools import wraps

def get_user_id():
    """
    Custom key function for user-based rate limiting
    Uses user ID for logged-in users, IP for anonymous users
    """
    if hasattr(request, 'endpoint') and current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return f"ip:{get_remote_address()}"

def get_user_and_ip():
    """
    Combination key function for stricter rate limiting
    Useful for critical operations like login attempts
    """
    user_part = f"user:{current_user.id}" if current_user and current_user.is_authenticated else "anonymous"
    ip_part = f"ip:{get_remote_address()}"
    return f"{user_part}:{ip_part}"

# Initialize rate limiter with Redis backend (recommended for production)
def create_limiter(app):
    """
    Create and configure Flask-Limiter with Redis backend
    Falls back to memory storage if Redis is unavailable
    """
    
    # Try to use Redis if available (production)
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    try:
        # Test Redis connection
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        
        # Use Redis for production
        limiter = Limiter(
            app=app,
            key_func=get_user_id,  # Default key function
            storage_uri=redis_url,
            default_limits=[
                "1000 per day",    # Daily limit per user/IP
                "200 per hour",    # Hourly limit per user/IP  
                "50 per 10 minutes" # Burst protection
            ],
            headers_enabled=True,  # Include rate limit headers in response
            strategy="fixed-window"  # Rate limiting strategy
        )
        
        print("✅ Rate Limiter: Using Redis storage backend")
        
    except (redis.RedisError, redis.ConnectionError):
        # Fallback to memory storage for development
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
        
        print("⚠️  Rate Limiter: Using memory storage (Redis unavailable)")
    
    return limiter

# 2. CUSTOM DECORATORS FOR SPECIFIC SCENARIOS
# =============================================================================

def strict_rate_limit(rate_limit_string):
    """
    Decorator for strict rate limiting using both user ID and IP
    Use for sensitive operations like login, password reset
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from extensions import limiter  # Import from your extensions
            
            # Apply rate limit using user+IP combination
            limiter.limit(rate_limit_string, key_func=get_user_and_ip)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def form_submission_limit(rate_limit_string="10 per minute"):
    """
    Decorator specifically for form submissions
    Prevents spam and abuse of forms
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from extensions import limiter
            
            # More restrictive for form submissions
            limiter.limit(rate_limit_string, key_func=get_user_id)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# 3. UPDATED EXTENSIONS.PY
# =============================================================================

# Add this to your extensions.py file:

"""
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from rate_limiter import create_limiter

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

# Rate limiter will be initialized in create_app()
limiter = None

def init_extensions(app):
    global limiter
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    limiter = create_limiter(app)  # Initialize rate limiter
    return limiter
"""

# 4. UPDATED APP.PY WITH RATE LIMITING
# =============================================================================

"""
# Add to your app.py imports:
from extensions import db, bcrypt, login_manager, init_extensions
from flask_limiter import Limiter

def create_app(test_config=None):
    app = Flask(__name__)
    
    # ... your existing configuration ...
    
    # Initialize extensions including rate limiter
    limiter = init_extensions(app)
    
    # Rate limiter error handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/rate_limit_exceeded.html', 
                             description=e.description), 429
    
    # ... rest of your app configuration ...
"""

# 5. UPDATED USER_ROUTES.PY WITH RATE LIMITING
# =============================================================================

"""
# Add these imports to your user_routes.py:
from flask_limiter import Limiter
from extensions import limiter
from rate_limiter import form_submission_limit, strict_rate_limit

# Update your feedback route:
@user.route('/feedback', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute", key_func=get_user_id)  # Prevent form spam
@limiter.limit("20 per hour", key_func=get_user_id)   # Hourly limit
def feedback():
    # Your existing feedback code...
    
# Update weather routes with rate limiting:
@user.route('/weather')
@login_required  
@limiter.limit("30 per minute")  # Prevent API abuse
def weather():
    # Your existing weather code...

@user.route('/weather-api')
@login_required
@limiter.limit("60 per minute")  # More generous for AJAX calls
def weather_api():
    # Your existing weather API code...

# Update notification routes:
@user.route('/notifications/<notification_id>/dismiss', methods=['POST'])
@login_required
@limiter.limit("100 per minute")  # Allow reasonable notification management
def dismiss_notification(notification_id):
    # Your existing code...
"""

# 6. AUTH ROUTES RATE LIMITING
# =============================================================================

"""
# Add to your auth_routes.py:
from extensions import limiter
from rate_limiter import strict_rate_limit

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute", key_func=get_user_and_ip)  # Prevent brute force
@limiter.limit("50 per hour", key_func=get_user_and_ip)    # Hourly protection
def login():
    # Your existing login code...

@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute", key_func=get_remote_address)  # Prevent account spam
@limiter.limit("10 per hour", key_func=get_remote_address)   # Hourly limit
def register():
    # Your existing registration code...

@auth.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour", key_func=get_remote_address)  # Prevent email spam
def forgot_password():
    # Your existing forgot password code...
"""

# 7. RATE LIMIT CONFIGURATION BY ROUTE TYPE
# =============================================================================

RATE_LIMIT_CONFIG = {
    # Authentication routes (stricter limits)
    'auth': {
        'login': ["10 per minute", "50 per hour"],
        'register': ["3 per minute", "10 per hour"], 
        'forgot_password': ["5 per hour"],
        'reset_password': ["10 per hour"]
    },
    
    # Form submission routes  
    'forms': {
        'feedback': ["5 per minute", "20 per hour"],
        'contact': ["3 per minute", "15 per hour"],
        'booking': ["10 per minute", "50 per hour"]
    },
    
    # API endpoints
    'api': {
        'weather': ["30 per minute"],
        'search': ["60 per minute"], 
        'data_export': ["5 per hour"]
    },
    
    # User management
    'user': {
        'profile_update': ["10 per minute"],
        'password_change': ["5 per hour"],
        'delete_account': ["1 per hour"]
    }
}

# 8. MONITORING AND LOGGING
# =============================================================================

def setup_rate_limit_monitoring(app, limiter):
    """
    Set up rate limit monitoring and logging
    """
    
    @limiter.request_filter
    def header_whitelist():
        """Skip rate limiting for health checks or admin endpoints"""
        # Skip rate limiting for health checks
        if request.endpoint == 'health_check':
            return True
        # Skip for admin users (if implemented)
        if current_user and current_user.is_authenticated and getattr(current_user, 'is_admin', False):
            return True
        return False
    
    @app.before_request
    def log_rate_limit_info():
        """Log rate limit information for monitoring"""
        if request.endpoint and limiter:
            try:
                # Get current limits for this endpoint
                current_limits = limiter.current_limits
                if current_limits:
                    app.logger.info(f"Rate limit check: {request.endpoint} - {get_user_id()}")
            except Exception as e:
                app.logger.warning(f"Rate limit logging error: {e}")

# 9. ENVIRONMENT VARIABLES
# =============================================================================

"""
Add to your .env file:

# Redis Configuration (optional, for production)
REDIS_URL=redis://localhost:6379

# Rate Limiting Configuration
RATELIMIT_STORAGE_URL=redis://localhost:6379
RATELIMIT_STRATEGY=fixed-window
RATELIMIT_HEADERS_ENABLED=true

# Rate Limit Values (optional customization)
DEFAULT_RATE_LIMIT_PER_DAY=1000
DEFAULT_RATE_LIMIT_PER_HOUR=200
DEFAULT_RATE_LIMIT_PER_MINUTE=50
"""

# 10. TESTING RATE LIMITS
# =============================================================================

"""
# Add to your test files:

def test_rate_limiting(client):
    # Test feedback form rate limiting
    for i in range(6):  # Exceed 5 per minute limit
        response = client.post('/feedback', data={
            'subject': f'Test {i}',
            'content': f'Test content {i}',
            'csrf_token': get_csrf_token(client)
        }, follow_redirects=True)
        
        if i >= 5:
            assert response.status_code == 429  # Rate limit exceeded
        else:
            assert response.status_code == 200

def test_login_rate_limiting(client):
    # Test login brute force protection
    for i in range(11):  # Exceed 10 per minute limit
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword',
            'csrf_token': get_csrf_token(client)
        })
        
        if i >= 10:
            assert response.status_code == 429
"""

# 11. DOCKER-COMPOSE FOR REDIS (OPTIONAL)
# =============================================================================

"""
# docker-compose.yml addition for Redis:

version: '3.8'
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

  app:
    # Your Flask app configuration
    depends_on:
      - redis
    environment:
      - REDIS_URL=redis://redis:6379

volumes:
  redis_data:
"""

print("✅ Rate Limiter Implementation Complete!")
print("🔒 OWASP A05:2021 Security Misconfiguration - ADDRESSED")
print("📋 Next Steps:")
print("1. pip install Flask-Limiter")
print("2. Update extensions.py with rate limiter initialization") 
print("3. Add rate limiting decorators to your routes")
print("4. Create rate_limit_exceeded.html template")
print("5. Optional: Set up Redis for production")
print("6. Test rate limits with your application")