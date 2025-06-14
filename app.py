from flask import Flask, render_template
from flask_login import LoginManager
from routes.auth_routes import auth
from routes.event_routes import event
from routes.user_routes import user
from routes.booking_routes import booking
from routes.chat_routes import chat
from routes.group_routes import group
from models.user import User  # your placeholder User class

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # TODO: Replace with an environment variable for production

# ---------- Flask-Login Setup ----------
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # redirect to login page if not logged in
login_manager.init_app(app)

# Dummy user store (to replace this with actual DB-backed queries)
users = {
    "1": User(1, "testuser", "testpass")
}

@login_manager.user_loader
def load_user(user_id):
    return users.get(user_id)

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

# ---------- Run App ----------
if __name__ == '__main__':
    app.run(debug=True)
