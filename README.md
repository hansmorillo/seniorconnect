# SeniorConnect

SeniorConnect is a secure web application designed to help seniors engage with their community by discovering events, joining interest groups, and booking shared spaces. Built with Flask, MySQL, and Bootstrap, the application demonstrates good security practices aligned with the OWASP Top 10 (2021) vulnerabilities.

---

## 🔧 Tech Stack

- **Frontend:** HTML, CSS, Bootstrap
- **Backend:** Python Flask
- **Database & ORM:** MySQL (PyMySQL driver), SQLAlchemy + Flask-SQLAlchemy
- **Forms & CSRF:** Flask-WTF, WTForms, ```email_validator```
- **Auth & Security:** Flask‑Login (sessions), Flask‑Bcrypt/bcrypt (password hashing), Flask‑Limiter (rate limits), Flask‑Talisman (security headers/CSP), bleach (sanitize), secure cookies (HttpOnly/SameSite/Secure), ```itsdangerous``` (signed tokens), ```python‑dotenv``` (secrets)
- **Email:** Flask-Mail (verification)
- **Utilities:** ```cryptography, requests```

---

## 📁 Project Structure

```
SeniorConnect/
├── app.py                  # Flask app entry point (uses create_app())
├── config.py               # DB and app configuration
├── extensions.py           # Flask extensions (db, bcrypt, login_manager, limiter, etc.)
├── requirements.txt        # Python dependencies
├── .env                    # Secret keys and DB credentials (not committed)
│
├── db/                     # SQL schema and initial seed data
├── forms/                  # Auth forms (register, login, logout)
├── logs/                   # Audit logs
├── models/                 # Database models (SQLAlchemy ORM)
├── routes/                 # All route Blueprints (Flask views/controllers)
├── static/                 # CSS, images, JavaScript
├── templates/              # HTML templates (includes base.html)
├── utils/                  # Utility functions (decorators, make_admin.py)
└── README.md
```

---

## 🌐 Available Routes (Blueprint-Based)

### 🔓 Guest Routes
| Route                   | Description                          |
|--------------------------|--------------------------------------|
| `/`                     | Landing page                         |
| `/register`             | Register new user (with reCAPTCHA)   |
| `/verify-email/<token>` | Verify pending account via email link|
| `/resend-verification`  | Resend verification email             |
| `/login`                | Login page (with reCAPTCHA)          |

---

### 🔒 Authenticated User Routes
| Route/Group         | Purpose                                        |
|---------------------|------------------------------------------------|
| `/logout` (POST)    | Log out of session (CSRF-protected)            |
| `/events`           | Browse events and RSVP/cancel attendance       |
| `/account`          | Manage account details                         |
| `/notifications/*`  | View, dismiss, mark all read, or clear all      |
| `/feedback`         | Submit user feedback                           |
| `/feedback/*` (Admin)| View or delete feedback (admin only)          |
| `/dashboard`        | User dashboard                                 |
| `/weather`          | Weather dashboard (Singapore) + `/weather-api` |
| `/booking/*`        | Create, confirm, manage, update, or cancel bookings |

---

###  System Routes
| Route      | Purpose             |
|------------|---------------------|
| `/health`  | Health check (JSON) |


---

##  Security Implementation

SeniorConnect is built with security in mind, following **OWASP Top 10 (2021)** practices:

| OWASP 2021 Risk                       | Implementation                                                                 |
|---------------------------------------|---------------------------------------------------------------------------------|
| **A01: Broken Access Control**        | `@login_required` decorators, role-based access for admin routes, secure cookies|
| **A02: Cryptographic Failures**       | `.env` for secrets, Flask-Bcrypt password hashing, HTTPS-ready deployment       |
| **A03: Injection**                    | SQLAlchemy ORM with parameterized queries, Jinja2 auto-escaping                  |
| **A04: Insecure Design**              | Defensive coding (CSRF on all forms, reCAPTCHA, rate limiting), admin-only decorators |
| **A05: Security Misconfiguration**    | Flask-Talisman for security headers (CSP, HSTS, X-Frame-Options), Flask-Limiter, `debug=False` in production |
| **A06: Vulnerable and Outdated Components** | Regular `pip-audit` / `pip list --outdated` checks, pinned versions in `requirements.txt` |
| **A07: Identification & Authentication Failures** | Flask-Login for session management, bcrypt password hashing, verified email flow |
| **A08: Software & Data Integrity Failures** | CSRF tokens via Flask-WTF, signed tokens (`itsdangerous`), email verification   |
| **A09: Security Logging & Monitoring Failures** | Python `logging` + audit logs for bookings                            |
| **A10: Server-Side Request Forgery (SSRF)** | Strict outbound calls (weather API only), environment variable API keys, timeout enforcement |


 Additional measures:  
- **Rate Limiting:** Flask-Limiter on sensitive endpoints (login, feedback, RSVP, bookings)  
- **Input Sanitization:** `bleach` for user-generated content (feedback, events)  
- **Cookie Security:** `HttpOnly`, `Secure`, `SameSite=Lax` set for all session cookies  
- **reCAPTCHA:** Protects login/registration against bots  


---

##  Getting Started

###  Installation

1. Clone the repo:
    ```bash
    git clone https://github.com/hansmorillo/seniorconnect
    cd seniorconnect
    ```

2. Set up a virtual environment:
    ```bash
    python -m venv venv        # Use 'py' if python isn't recognized
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file with your local credentials:
    ```env
    SECRET_KEY=your-secret-key
    DB_USER=root
    DB_PASSWORD=password
    DB_HOST=localhost
    DB_NAME=seniorconnect

    OPEN_WEATHER=open_weather_api_key

    MAIL_SERVER=mail.server.com
    MAIL_PORT=mail_port
    MAIL_USE_TLS=True
    MAIL_USE_SSL=False
    MAIL_USERNAME=email_to_send_verification_email
    MAIL_PASSWORD=mail_password
    MAIL_DEFAULT_SENDER=default_email_to_send_verification_email

    RECAPTCHA_PUBLIC_KEY=v2_public_key
    RECAPTCHA_PRIVATE_KEY=v2_private_key
    ```

    Feel free to reach out to me at hansmorillo07@gmail.com for credentials to test the application.

5. Initialize the database:
    ```sql
    SOURCE db/live_schema.sql;
    SOURCE db/seed_data_seniorconnect.sql;
    ```

###  Run the App

```bash
python app.py
```

This will launch the Flask server using the `create_app()` pattern.
The app runs at https://127.0.0.1:5000/ by default.

---

## 📌 Completed Milestones

- ✅ MySQL-backed login, pending user flow, and email verification
- ✅ Secure password hashing with Flask-Bcrypt
- ✅ reCAPTCHA protection on login and registration
- ✅ CSRF protection on all forms via Flask-WTF
- ✅ Blueprinted routes for auth, events, bookings, and users
- ✅ Session management with Flask-Login (secure cookies)
- ✅ Notifications system (create, dismiss, mark-all-read, clear-all)
- ✅ Event management with RSVP + notifications
- ✅ Booking system with validation, manage/update/cancel, audit logs
- ✅ User feedback submission with sanitization + admin feedback dashboard
- ✅ Weather dashboard with external API integration (SG-only)
- ✅ Role-based access control for admins vs seniors

---

##  Authors

- Hans Morillo
- Royston Kee
- Shavonne Tang

---

##  License

This project is intended for academic purposes and follows the submission guidelines for the Application Security Project IT2555.
