from flask import Flask, render_template
from dotenv import load_dotenv
from datetime import timedelta
import os

from extensions import db, bcrypt, login_manager, limiter
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

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')

    # ---------- Database Stuff ----------
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Initialize Extensions ----------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    # CSRF 
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
