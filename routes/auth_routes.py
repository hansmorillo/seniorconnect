from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_login import login_user, logout_user, login_required
from flask_mail import Message
from models.user import User, PendingUser
from extensions import db, bcrypt, mail
import uuid
import secrets
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)

def send_verification_email(email, token):
    """Send verification email to user"""
    try:
        msg = Message(
            'Verify Your SeniorConnect Account',
            recipients=[email]
        )
        
        verification_link = url_for('auth.verify_email', token=token, _external=True)
        
        msg.body = f'''
Welcome to SeniorConnect!

Please click the following link to verify your email address and activate your account:
{verification_link}

This verification link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
The SeniorConnect Team
'''
        
        msg.html = f'''
<html>
<body>
    <h2>Welcome to SeniorConnect!</h2>
    <p>Please click the button below to verify your email address and activate your account:</p>
    <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Verify Email</a>
    <p>Or copy and paste this link into your browser:</p>
    <p>{verification_link}</p>
    <p><small>This verification link will expire in 24 hours.</small></p>
    <p>If you didn't create this account, please ignore this email.</p>
    <p>Best regards,<br>The SeniorConnect Team</p>
</body>
</html>
'''
        
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Debug: Print that we received a POST request
        print("🚀 Registration POST request received")
        
        # Debug: Check CSRF token
        try:
            from flask_wtf.csrf import validate_csrf
            validate_csrf(request.form.get('csrf_token'))
            print("✅ CSRF token validated")
        except Exception as e:
            print(f"❌ CSRF validation failed: {e}")
            flash('Security validation failed. Please try again.', 'error')
            return render_template('register.html')
        
        display_name = request.form.get('display_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        # Debug: Print form data (without password)
        print(f"📝 Form data - Name: {display_name}, Email: {email}, Phone: {phone}")

        # Basic validation
        if not all([display_name, email, phone, password]):
            flash('All fields are required.', 'error')
            print("❌ Validation failed: Missing fields")
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            print("❌ Validation failed: Password too short")
            return render_template('register.html')

        # Check if email already exists in verified users
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please log in.', 'warning')
            print(f"⚠️ Email {email} already exists in verified users")
            return redirect(url_for('auth.login'))

        # Check if email already has pending verification
        pending_user = PendingUser.query.filter_by(email=email).first()
        if pending_user:
            # Remove old pending verification if it exists
            print(f"🗑️ Removing old pending verification for {email}")
            db.session.delete(pending_user)
            db.session.commit()

        # Hash the password
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        print("🔐 Password hashed successfully")

        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Create pending user (not verified yet)
        pending_user = PendingUser(
            display_name=display_name,
            email=email,
            phone_number=phone,
            password_hash=hashed_pw,
            verification_token=verification_token,
            expires_at=datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
        )

        try:
            # Save pending user to database
            print("💾 Attempting to save pending user to database")
            db.session.add(pending_user)
            db.session.commit()
            print("✅ Pending user saved successfully")

            # Send verification email
            print("📧 Attempting to send verification email")
            if send_verification_email(email, verification_token):
                print("✅ Verification email sent successfully")
                flash('Registration successful! Please check your email for a verification link.', 'success')
                return render_template('verify_email_sent.html', email=email)
            else:
                print("❌ Failed to send verification email")
                # If email sending fails, remove the pending user
                db.session.delete(pending_user)
                db.session.commit()
                flash('Failed to send verification email. Please try again.', 'error')
                return render_template('register.html')
                
        except Exception as e:
            print(f"❌ Database error during registration: {e}")
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('register.html')

    # GET request - show the form
    print("📄 Showing registration form")
    return render_template('register.html')

@auth.route('/verify-email/<token>')
def verify_email(token):
    """Verify email address using the token"""
    # Find pending user with this token
    pending_user = PendingUser.query.filter_by(verification_token=token).first()
    
    if not pending_user:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('auth.register'))
    
    # Check if token has expired
    if datetime.utcnow() > pending_user.expires_at:
        # Clean up expired pending user
        db.session.delete(pending_user)
        db.session.commit()
        flash('Verification link has expired. Please register again.', 'error')
        return redirect(url_for('auth.register'))
    
    try:
        # Create verified user
        new_user = User(
            id=str(uuid.uuid4()),
            display_name=pending_user.display_name,
            email=pending_user.email,
            phone_number=pending_user.phone_number,
            password_hash=pending_user.password_hash,
            is_verified=True
        )
        
        # Add to database and remove pending user
        db.session.add(new_user)
        db.session.delete(pending_user)
        db.session.commit()
        
        flash('Email verified successfully! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        db.session.rollback()
        flash('Verification failed. Please try again.', 'error')
        print(f"Verification error: {e}")
        return redirect(url_for('auth.register'))

@auth.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    email = request.form.get('email', '').strip().lower()
    
    if not email:
        flash('Email is required.', 'error')
        return redirect(url_for('auth.register'))
    
    # Check if user is already verified
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('This email is already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))
    
    # Find pending user
    pending_user = PendingUser.query.filter_by(email=email).first()
    if not pending_user:
        flash('No pending registration found for this email.', 'error')
        return redirect(url_for('auth.register'))
    
    # Update expiry time
    pending_user.expires_at = datetime.utcnow() + timedelta(hours=24)
    pending_user.verification_token = secrets.token_urlsafe(32)  # Generate new token
    
    try:
        db.session.commit()
        
        if send_verification_email(email, pending_user.verification_token):
            flash('Verification email resent! Please check your inbox.', 'success')
            return render_template('verify_email_sent.html', email=email)
        else:
            flash('Failed to send verification email. Please try again.', 'error')
            return redirect(url_for('auth.register'))
            
    except Exception as e:
        db.session.rollback()
        flash('Failed to resend verification email.', 'error')
        print(f"Resend verification error: {e}")
        return redirect(url_for('auth.register'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return render_template('login.html')
            
            login_user(user)
            return redirect(url_for('home'))
        else:
            # Check if user has pending verification
            pending_user = PendingUser.query.filter_by(email=email).first()
            if pending_user:
                flash('Please verify your email address to complete registration.', 'info')
            else:
                flash('Invalid credentials', 'error')

    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))