from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_user, logout_user, login_required
from models.user import User
from extensions import db, bcrypt, limiter  # using shared instances from extensions.py
import uuid
from forms.auth_forms import LoginForm, RegisterForm

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        display_name = form.display_name.data
        email = form.email.data
        phone = form.phone.data
        password = form.password.data

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'warning')
            return redirect(url_for('auth.login'))

        # Hash the password
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create a new user
        new_user = User(
            id=str(uuid.uuid4()),           # Generate UUID for user, not incremental
            display_name=display_name,
            email=email,
            phone_number=phone,
            password_hash=hashed_pw
        )

        # Save to DB
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limit login attempts
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        remember = form.remember.data

        # Fetch user from DB
        user = User.query.filter_by(email=email).first()

        # Verify credentials
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))  
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))