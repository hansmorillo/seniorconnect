from flask import Blueprint, render_template, request, redirect, flash, url_for, abort
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse
from models.user import User
from extensions import db, bcrypt, limiter  # using shared instances from extensions.py
import uuid
from forms.auth_forms import LoginForm, RegisterForm, LogoutForm
from datetime import timedelta  

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if request.method == 'POST':
        print("=== REGISTRATION DEBUG ===")
        print(f"Display Name: {form.display_name.data}")
        print(f"Email: {form.email.data}")
        print(f"Phone: {form.phone.data}")
        
        # Check reCAPTCHA response from form data
        recaptcha_response = request.form.get('g-recaptcha-response')
        print(f"reCAPTCHA response present: {bool(recaptcha_response)}")
        print(f"reCAPTCHA response length: {len(recaptcha_response) if recaptcha_response else 0}")
        
        # First check if reCAPTCHA response exists before form validation
        if not recaptcha_response:
            flash('Please complete the reCAPTCHA verification', 'danger')
            return render_template('register.html', form=form)
        
        # Validate the form (this will also validate reCAPTCHA)
        if form.validate_on_submit():
            print("✅ Form validation passed")
            
            display_name = form.display_name.data
            email = form.email.data.lower().strip()  # Ensure consistent email format
            phone = form.phone.data.replace(' ', '')  # Remove spaces from phone
            password = form.password.data

            # Double-check if email already exists (additional safety check)
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please log in.', 'warning')
                return redirect(url_for('auth.login'))

            # Hash the password
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

            # Create a new user
            new_user = User(
                id=str(uuid.uuid4()),           # Generate UUID for user
                display_name=display_name,
                email=email,
                phone_number=phone,
                password_hash=hashed_pw
            )

            try:
                # Save to DB
                db.session.add(new_user)
                db.session.commit()
                print(f"✅ User created successfully: {email}")
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('auth.login'))
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Database error during registration: {e}")
                flash('An error occurred during registration. Please try again.', 'danger')
                return render_template('register.html', form=form)
        else:
            # Form validation failed
            print("❌ Form validation failed:")
            print("Form errors:", form.errors)
            
            # Check specifically for reCAPTCHA errors
            if 'recaptcha' in form.errors:
                print("reCAPTCHA validation error:", form.errors['recaptcha'])
                flash('reCAPTCHA verification failed. Please try again.', 'danger')
            else:
                flash('Please fix the errors below.', 'danger')
            
            return render_template('register.html', form=form)

    # GET request - just show the form
    return render_template('register.html', form=form)

@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Rate limit login attempts
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    form = LoginForm()

    if form.validate_on_submit():
        print("=== LOGIN DEBUG ===")
        
        # Check reCAPTCHA response
        recaptcha_response = request.form.get('g-recaptcha-response')
        print(f"reCAPTCHA response present: {bool(recaptcha_response)}")
        
        if not recaptcha_response:
            flash('Please complete the reCAPTCHA verification', 'danger')
            return render_template('login.html', form=form)

        email = form.email.data.lower().strip()
        password = form.password.data
        remember = bool(getattr(form, "remember", None) and form.remember.data)

        print(f"Login attempt for email: {email}")

        user = User.query.filter_by(email=email).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            print(f"❌ Login failed for: {email}")
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=form), 401

        login_user(
            user,
            remember=remember,
            duration=timedelta(days=30)
        )

        print(f"✅ Login successful for: {email}")

        next_page = request.args.get("next")
        if not next_page or urlparse(next_page).netloc != "":
            next_page = url_for("home")
        
        flash("Logged in successfully!", "success")
        return redirect(next_page)
    else:
        # Login form validation failed
        if request.method == 'POST':
            print("❌ Login form validation failed:")
            print("Form errors:", form.errors)
            
            if 'recaptcha' in form.errors:
                flash('reCAPTCHA verification failed. Please try again.', 'danger')
            else:
                flash('Please check your login details.', 'danger')

    return render_template("login.html", form=form)


@auth.route('/logout', methods=['POST'])
@login_required
def logout():
    form = LogoutForm()
    if not form.validate_on_submit():  # ensures CSRF is valid
        abort(400)
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))