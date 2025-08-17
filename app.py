from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os

from extensions import db, bcrypt, login_manager, csrf, limiter
from routes.auth_routes import auth
from routes.event_routes import event
from routes.user_routes import user
from routes.booking_routes import booking  # Remove limiter import - we'll create it here
from routes.chat_routes import chat
from routes.group_routes import group
from models.user import User
from models.booking import Booking
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from datetime import datetime

# ---------- Load Environment Variables ----------
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret')
    app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB

    # ---------- Database Stuff ----------
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

    # ---------- Initialize Extensions ----------
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.login_view = 'auth.login'

    # ---------- User Loader ----------
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    # ---------- Register Blueprints ----------
    app.register_blueprint(auth)
    app.register_blueprint(event)
    app.register_blueprint(user)
    app.register_blueprint(booking)  # ⬅️ must happen before we bind limits
    app.register_blueprint(chat)
    app.register_blueprint(group)

    # ---------- Error Handlers ----------
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        flash('Security validation failed (CSRF). Please try again.', 'error')
        return redirect(url_for('booking.booking_main')), 400
    
    @app.errorhandler(429)
    def handle_rate_limit_error(e):
        print(f"🚨 RATE LIMIT HIT: {e.description}")
        
        # Check if it's an AJAX request
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'error': 'Too many requests. Please wait a moment before trying again.',
                'rate_limited': True
            }), 429
        
        # For regular form submissions
        flash('Too many requests. Please wait a moment before trying again.', 'error')
        return redirect(url_for('booking.booking_main')), 429

    # ---------- Rate Limit Test Route (for debugging) ----------
    @app.route('/test-rate-limit')
    @limiter.limit("2 per minute")
    def test_rate_limit():
        return jsonify({
            'message': 'Rate limit test successful',
            'timestamp': str(datetime.now())
        })

    # ---------- Create Tables ----------
    with app.app_context():
        db.create_all()

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
    from datetime import datetime
    app = create_app()
    print("🚀 Flask app started with rate limiting enabled!")
    app.run(debug=True)