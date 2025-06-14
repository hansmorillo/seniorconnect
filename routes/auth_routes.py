from flask import Blueprint, render_template, redirect, url_for
from flask_login import logout_user, login_required, login_user # login_user temporary for simulate login testing
from models.user import User

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/register')
def register():
    return render_template('register.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

# temporarry route to simulate login
@auth.route('/simulate-login')
def simulate_login():
    user = User(1, 'testuser', 'testpass')
    login_user(user)
    return redirect(url_for('home'))
