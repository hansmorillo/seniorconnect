# app.py - FIXED VERSION - Correct imports for rate limiting
from flask import Flask, render_template, request  
from flask_login import current_user  # 🔒 CORRECT: Import current_user from flask_login
from dotenv import load_dotenv
import os
from flask_talisman import Talisman  
from flask_wtf.csrf import CSRFProtect
from extensions import db, bcrypt, login_manager, init_extensions
from models.user import User
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS

# ---------- Load Environment Variables ----------
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    
    # ---------- Configuration ----------
    if test_config:
        app.config.update(test_config)
    else:
        app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')
        app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Initialize Extensions INCLUDING RATE LIMITER ----------
    limiter = init_extensions(app)
    
    # Initialize CSRF Protection
    csrf = CSRFProtect(app)

    # ---------- Security Headers with Talisman (skip for testing) ----------
    if not app.config.get('TESTING', False):
        Talisman(
            app,
            content_security_policy={
                'default-src': "'self'",
                'script-src': ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com", "cdn.jsdelivr.net"],
                'style-src': ["'self'", "'unsafe-inline'", "cdnjs.cloudflare.com", "cdn.jsdelivr.net", "fonts.googleapis.com"],
                'font-src': ["'self'", "fonts.gstatic.com", "cdnjs.cloudflare.com"],
                'img-src': ["'self'", "data:", "openweathermap.org", "*"],
                'connect-src': ["'self'", "api.openweathermap.org"]
            },
            force_https=False
        )

    # ---------- User Loader ----------
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # ---------- Rate Limiter Configuration ----------
    @limiter.request_filter
    def header_whitelist():
        """Skip rate limiting for health checks or admin endpoints"""
        if hasattr(request, 'endpoint') and request.endpoint == 'health_check':
            return True
        try:
            if current_user and current_user.is_authenticated and getattr(current_user, 'is_admin', False):
                return True
        except:
            pass
        return False

    # ---------- Import and Register Blueprints AFTER limiter is initialized ----------
    from routes.auth_routes import auth
    from routes.event_routes import event
    from routes.user_routes import user
    from routes.booking_routes import booking
    from routes.chat_routes import chat
    from routes.group_routes import group
    
    app.register_blueprint(auth)
    app.register_blueprint(event)
    app.register_blueprint(user)
    app.register_blueprint(booking)
    app.register_blueprint(chat)
    app.register_blueprint(group)

    # ---------- Public Routes WITH Rate Limiting ----------
    @app.route('/')
    @limiter.limit("100 per minute")
    def home():
        return render_template('index.html')

    @app.route('/about')
    @limiter.limit("50 per minute")
    def about():
        return render_template('about.html')

    # ---------- Health Check (No Rate Limiting) ----------
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'seniorconnect'}, 200

    # ---------- Error Handlers ----------
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(400)
    def csrf_error(reason):
        return render_template('errors/csrf_error.html', reason=reason), 400
    
    # 🔒 Rate Limit Error Handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/rate_limit_exceeded.html', 
                             description=e.description), 429

    return app

# ---------- Run App ----------
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)