from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_user, logout_user, login_required
from models.user import User
from extensions import db, bcrypt  # using shared instances from extensions.py
import uuid

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        display_name = request.form['display_name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(id=str(uuid.uuid4()), display_name=display_name, email=email,
                        phone_number=phone, password_hash=hashed_pw)

        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))