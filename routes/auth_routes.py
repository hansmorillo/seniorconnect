from flask import Blueprint, render_template, request, redirect, flash, url_for, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from models.user import User, PendingUser
from extensions import db, bcrypt, mail, limiter
from forms.auth_forms import LoginForm, LogoutForm, RegisterForm
import uuid
import secrets
from datetime import datetime, timedelta
from sqlalchemy import or_

auth = Blueprint('auth', __name__)

# -----------------------------------------
# Helpers
# -----------------------------------------

def _normalize(s: str) -> str:
    return (s or "").strip()

def _send_verification_email(email: str, token: str) -> bool:
    """
    Sends a verification email with a one-time token. Returns True on success.
    """
    try:
        verification_link = url_for("auth.verify_email", token=token, _external=True)

        sender = current_app.config.get('MAIL_DEFAULT_SENDER') or current_app.config.get('MAIL_USERNAME')
        if not sender:
            raise RuntimeError("MAIL_DEFAULT_SENDER/MAIL_USERNAME not set")

        msg = Message(
            subject="Verify Your SeniorConnect Account",
            recipients=[email],
            sender=sender
        )
        # Plain text
        msg.body = (
            "Welcome to SeniorConnect!\n\n"
            "Please click the following link to verify your email address and activate your account:\n"
            f"{verification_link}\n\n"
            "This verification link will expire in 24 hours.\n\n"
            "If you didn't create this account, please ignore this email.\n\n"
            "Best regards,\nThe SeniorConnect Team\n"
        )
        # Simple HTML version
        msg.html = f"""
            <html>
                <body>
                    <h2>Welcome to SeniorConnect!</h2>
                    <p>Please click the button below to verify your email address and activate your account:</p>
                    <p>
                        <a href="{verification_link}" style="background:#4CAF50;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none;">
                            Verify Email
                        </a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p>{verification_link}</p>
                    <p><small>This verification link will expire in 24 hours.</small></p>
                    <p>If you didn't create this account, please ignore this email.</p>
                    <p>Best regards,<br>The SeniorConnect Team</p>
                </body>
            </html>
        """
        mail.send(msg)
        return True
    except Exception as e:
        # Log server-side
        print(f"[auth] Failed to send verification email to {email}: {e}")
        return False


def _already_verified_conflict(email: str, phone: str) -> bool:
    """
    True if a *verified* User exists with either this email or phone.
    (Phone check optional—use it if your User table enforces phone uniqueness.)
    """
    q = [User.email == email]
    if phone:
        q.append(User.phone_number == phone)
    return db.session.query(User.id).filter(or_(*q)).first() is not None


def _purge_expired_pending_for(email: str) -> None:
    """
    Remove any expired PendingUser rows for this email.
    """
    db.session.query(PendingUser).filter(
        PendingUser.email == email,
        PendingUser.expires_at < datetime.utcnow()
    ).delete(synchronize_session=False)
    db.session.commit()

def _pending_active_conflict(email: str) -> PendingUser | None:
    """
    Returns a *live* (not expired) PendingUser for this email, if any.
    """
    return PendingUser.query.filter(
        PendingUser.email == email,
        PendingUser.expires_at >= datetime.utcnow()
    ).first()

def _hash_password(plaintext: str) -> str:
    return bcrypt.generate_password_hash(plaintext).decode("utf-8")

def _check_password(user: User, plaintext: str) -> bool:
    """
    Support both a model helper (user.check_password) and direct bcrypt usage.
    """
    checker = getattr(user, "check_password", None)
    if callable(checker):
        return checker(plaintext)
    return bcrypt.check_password_hash(user.password_hash, plaintext)


# -----------------------------------------
# Routes
# -----------------------------------------

@auth.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def register():
    # If the user is already logged in, bounce them “home”
    if getattr(current_user, "is_authenticated", False):
        return redirect(url_for("home"))

    form = RegisterForm()

    if request.method == 'POST':
        # 1) Require a reCAPTCHA response to even attempt validation
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not recaptcha_response:
            flash('Please complete the reCAPTCHA verification.', 'danger')
            return render_template('register.html', form=form)

        # 2) Validate full form (this will also validate RecaptchaField if present)
        if not form.validate_on_submit():
            # Keep the user on the same page; do NOT redirect
            if 'recaptcha' in getattr(form, 'errors', {}):
                flash('reCAPTCHA verification failed. Please try again.', 'danger')
            else:
                flash('Please fix the errors below.', 'danger')
            return render_template('register.html', form=form)

        # 3) Proceed with your pending-user flow
        display_name = form.display_name.data
        email = (form.email.data or '').strip().lower()
        phone = (getattr(form, 'phone', None).data if hasattr(form, 'phone') else
                 getattr(form, 'phone_number', None).data if hasattr(form, 'phone_number') else '')
        phone = (phone or '').strip()
        password = form.password.data

        # 1) Hard-stop if verified user exists
        if _already_verified_conflict(email, phone):
            flash("That email/phone is already registered. Try logging in.", "danger")
            return render_template("register.html", form=form), 400

        # 2) Purge any expired pendings for this email, then check for live pending conflicts
        _purge_expired_pending_for(email)
        live_pending = _pending_active_conflict(email)
        if live_pending:
            # (Optional) Replace the existing pending with a fresh token/expiry and re-send.
            live_pending.display_name = display_name  # keep newest name/phone if you want
            live_pending.phone_number = phone
            live_pending.password_hash = _hash_password(password)
            live_pending.verification_token = secrets.token_urlsafe(32)
            live_pending.expires_at = datetime.utcnow() + timedelta(hours=24)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"[auth] Could not update existing PendingUser for {email}: {e}")
                flash("Registration failed. Please try again.", "danger")
                return render_template("register.html", form=form), 500

            if _send_verification_email(email, live_pending.verification_token):
                flash("We found a pending signup—sent a fresh verification link. Check your inbox.", "info")
                return render_template("verify_email_sent.html", email=email)
            else:
                flash("We couldn't send a verification email. Please try again.", "danger")
                return render_template("register.html", form=form), 502

        # 3) Create new pending registration
        pending = PendingUser(
            display_name=display_name,
            email=email,
            phone_number=phone,
            password_hash=_hash_password(password),
            verification_token=secrets.token_urlsafe(32),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )

        try:
            db.session.add(pending)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[auth] DB error creating PendingUser for {email}: {e}")
            flash("Registration failed. Please try again.", "danger")
            return render_template("register.html", form=form), 500

        # 4) Send verification mail
        if _send_verification_email(email, pending.verification_token):
            flash("Registration successful! Check your email to verify your account.", "success")
            return render_template("verify_email_sent.html", email=email)
        else:
            # If email fails, clean up the pending row to avoid dead entries
            try:
                db.session.delete(pending)
                db.session.commit()
            except Exception:
                db.session.rollback()
            flash("We couldn't send a verification email. Please try again.", "danger")
            return render_template("register.html", form=form), 502

    # GET (or any non-POST)
    return render_template("register.html", form=form)


@auth.route("/verify-email/<token>")
def verify_email(token: str):
    """
    Promote a PendingUser with a valid token to a full User record.
    """
    pending = PendingUser.query.filter_by(verification_token=token).first()
    if not pending:
        flash("Invalid or expired verification link.", "danger")
        return redirect(url_for("auth.register"))

    if datetime.utcnow() > pending.expires_at:
        # Expired token → delete the stale row
        try:
            db.session.delete(pending)
            db.session.commit()
        except Exception:
            db.session.rollback()
        flash("Verification link expired. Please register again.", "warning")
        return redirect(url_for("auth.register"))

    # Create verified user (id: uuid4)
    user = User(
        id=str(uuid.uuid4()),
        display_name=pending.display_name,
        email=pending.email,
        phone_number=pending.phone_number,
        password_hash=pending.password_hash,
        is_verified=True,
    )

    try:
        db.session.add(user)
        db.session.delete(pending)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[auth] Error promoting PendingUser to User for {pending.email}: {e}")
        flash("Verification failed. Please try again.", "danger")
        return redirect(url_for("auth.register"))

    flash("Email verified! You can now sign in.", "success")
    return redirect(url_for("auth.login"))


@auth.route("/resend-verification", methods=["POST"])
@limiter.limit("2 per minute")  # Throttle brute-force attempts
def resend_verification():
    """
    Re-issue a verification email for an existing (non-expired) PendingUser.
    Expects a form POST that includes 'email'.
    """
    email = _normalize(request.form.get("email", "")).lower()
    if not email:
        flash("Email is required.", "danger")
        return redirect(url_for("auth.register"))

    # If already a verified user, guide them to sign in
    if User.query.filter_by(email=email).first():
        flash("That email is already verified. Try signing in.", "info")
        return redirect(url_for("auth.login"))

    # Refresh the token/expiry on an existing pending row (or let users re-register if none)
    pending = _pending_active_conflict(email)
    if not pending:
        flash("We couldn't find a pending registration for that email. Please register again.", "warning")
        return redirect(url_for("auth.register"))

    pending.verification_token = secrets.token_urlsafe(32)
    pending.expires_at = datetime.utcnow() + timedelta(hours=24)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[auth] DB error refreshing PendingUser for {email}: {e}")
        flash("We couldn't re-issue the verification email. Please try again.", "danger")
        return redirect(url_for("auth.register"))

    if _send_verification_email(email, pending.verification_token):
        flash("Verification email re-sent. Please check your inbox.", "success")
        return render_template("verify_email_sent.html", email=email)
    else:
        flash("We couldn't send a verification email. Please try again.", "danger")
        return redirect(url_for("auth.register"))


@auth.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def login():
    # Already logged in? Go home.
    if getattr(current_user, "is_authenticated", False):
        return redirect(url_for("home"))

    form = LoginForm()

    if request.method == 'POST':
        # 1) Require a reCAPTCHA response before attempting validation
        recaptcha_response = request.form.get('g-recaptcha-response')
        if not recaptcha_response:
            flash('Please complete the reCAPTCHA verification.', 'danger')
            return render_template('login.html', form=form)

        # 2) Validate the form (this should also validate RecaptchaField if present)
        if not form.validate_on_submit():
            if 'recaptcha' in getattr(form, 'errors', {}):
                flash('reCAPTCHA verification failed. Please try again.', 'danger')
            else:
                flash('Please check your login details.', 'danger')
            return render_template('login.html', form=form)

        # 3) Proceed with normal login flow
        email = _normalize(form.email.data).lower()
        password = form.password.data
        remember = bool(getattr(form, "remember", None) and form.remember.data)

        user = User.query.filter_by(email=email).first()

        if user and _check_password(user, password):
            # Require verified account before login
            if not getattr(user, "is_verified", False):
                flash("Please verify your email before signing in.", "warning")
                return render_template("login.html", form=form), 403

            # Respect app-level remember duration unless you explicitly pass one
            login_user(user, remember=remember)  # or duration=timedelta(days=30)
            flash("Welcome back!", "success")

            # Safe handling of ?next=
            next_page = request.args.get("next")
            try:
                from urllib.parse import urlparse
                if not next_page or urlparse(next_page).netloc != "":
                    next_page = url_for("home")
            except Exception:
                next_page = url_for("home")

            return redirect(next_page)

        # Not a verified user—check if there’s a pending registration
        if PendingUser.query.filter_by(email=email).first():
            flash("We found a pending registration—please verify your email.", "info")
        else:
            flash("Invalid email or password.", "danger")

        # Fall through to render the form again after flashing messages

    # GET or re-render after POST
    return render_template("login.html", form=form)



@auth.route("/logout", methods=["POST"])
@login_required
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def logout():
    form = LogoutForm()
    if not form.validate_on_submit():  # CSRF validation
        abort(400)
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("home"))