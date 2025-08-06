#app.py
from flask import Flask, render_template
from dotenv import load_dotenv
import os
from flask_talisman import Talisman  
from extensions import db, bcrypt, login_manager
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
    
    # ---------- Configuration ----------
    if test_config:
        # Use test configuration
        app.config.update(test_config)
    else:
        # Use production/development configuration
        app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')
        app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Initialize Extensions ----------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

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
            force_https=False  # Set to False for development
        )

    # ---------- User Loader ----------
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # ---------- Register Blueprints ----------
    app.register_blueprint(auth)
    app.register_blueprint(event)
    app.register_blueprint(user)
    app.register_blueprint(booking)
    app.register_blueprint(chat)
    app.register_blueprint(group)

    # ---------- Public Routes ----------
    @app.route('/')
    def home():
        return render_template('index.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    return app

# ---------- Run App ----------
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)