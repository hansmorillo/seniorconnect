from flask import Flask, render_template, request  
from flask_login import current_user  
from dotenv import load_dotenv
from datetime import timedelta
import os

from extensions import db, bcrypt, login_manager, limiter, csrf
from routes.auth_routes import auth
from routes.event_routes import event
from routes.user_routes import user
from routes.booking_routes import booking
from routes.chat_routes import chat
from routes.group_routes import group
from models.user import User
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS

# ---------- Load Environment Variables ----------
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    
    
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')

    # Database Setup
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Initialize Extensions ----------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # CSRF
    csrf.init_app(app)  # Initialize CSRF protection with Flask-WTF
    app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF protection using Flask-WTF
    # Session & Cookie Configuration
    app.config['SESSION_COOKIE_SECURE'] = True # Only send cookies via HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to cookies
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
    # Rate Limiting
    limiter.init_app(app)
    # Remember Me / Stay Logged In
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)
    app.config['REMEMBER_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
    # ---------- User Loader ----------
    @login_manager.user_loader
    def load_user(user_id: str):
        session = db.session
        return session.get(User, user_id)  # SQLAlchemy API get method
    
    app.register_blueprint(auth)
    app.register_blueprint(event)
    app.register_blueprint(user)
    app.register_blueprint(booking)

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