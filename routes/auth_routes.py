from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User
from extensions import db, bcrypt, limiter  # using shared instances from extensions.py
import uuid
from forms.auth_forms import LoginForm, RegisterForm
from datetime import timedelta

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    # Optional: log to see what's failing

    if request.method == 'POST' and not form.validate():
        # Stay on the same page; do NOT redirect
        flash('Please fix the errors below.', 'danger')
        return render_template('register.html', form=form)

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
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()

    if form.validate_on_submit():
        email = (form.email.data or "").lower()
        password = form.password.data
        remember = bool(getattr(form, "remember", None) and form.remember.data)

        user = User.query.filter_by(email=form.email.data).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=form), 401

        login_user(
            user,
            remember=remember,
            duration=timedelta(days=30)  # optional; can also set in app.config
        )

        next_page = request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("home")
        flash("Logged in successfully!", "success")
        return redirect(next_page)

    return render_template("login.html", form=form)


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))