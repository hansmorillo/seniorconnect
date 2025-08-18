from flask import Flask, render_template, request
from dotenv import load_dotenv
from datetime import timedelta
import os

from extensions import db, bcrypt, login_manager, csrf, limiter, mail
from routes.auth_routes import auth
from routes.event_routes import event
from routes.user_routes import user
from routes.booking_routes import booking  
from models.user import User, PendingUser
from models.booking import Booking
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime

# ---------- Load Environment Variables ----------
load_dotenv()

def create_app(test_config=None):
    app = Flask(__name__)
    
    
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB

    # Database Setup
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Mail Configuration ----------
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

    # ---------- Initialize Extensions ----------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
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


    @app.route('/')
    @limiter.limit("100 per minute")
    def home():
        return render_template('index.html')

    @app.route('/about')
    @limiter.limit("50 per minute")
    def about():
        return render_template('about.html')
    
    # ---------- Context Processors ------------------------------------------------
    from forms.auth_forms import LogoutForm

    @app.context_processor
    def inject_logout_form():
        """
        Inject a LogoutForm instance into every template.

        Used by the navbar to POST /logout with a valid CSRF token without having to
        pass the form explicitly in each render_template(...).
        """
        return {"logout_form": LogoutForm()}

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