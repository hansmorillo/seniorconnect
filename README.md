# SeniorConnect

SeniorConnect is a secure web application designed to help seniors engage with their community by discovering events, joining interest groups, and booking shared spaces. Built with Flask, MySQL, and Bootstrap, the application demonstrates good security practices aligned with the OWASP Top 10 (2019) vulnerabilities.

---

## 🔧 Tech Stack

- **Frontend:** HTML, CSS, Bootstrap
- **Backend:** Python Flask
- **Database:** MySQL
- **Authentication:** Flask-Login, Flask-Bcrypt
- **Security Modules:** Flask-Limiter, Flask-WTF, Flask-Login
- **Hosting:** Render Deployment in future

---

## 📁 Project Structure

```
SeniorConnect/
├── app.py                  # Flask app entry point (uses create_app())
├── config.py               # DB and app configuration
├── extensions.py           # Flask extensions (db, bcrypt, login_manager)
├── models/                 # ORM-like Python classes
├── routes/                 # All route Blueprints
├── templates/              # HTML templates (Jinja2)
├── static/                 # CSS, images, scripts
├── db/                     # SQL schema and seed files
├── forms/                  # Form folder to separate from routes and models
├── requirements.txt        # Python dependencies
├── .env                    # Secret keys and DB credentials (not committed)
└── README.md
```

---

## 🌐 Available Routes (Blueprint-Based)

### 🔓 Guest Routes

| Route        | Description             |
|--------------|-------------------------|
| `/`          | Landing page            |
| `/about`     | About Us page           |
| `/login`     | Login page              |
| `/register`  | Register new user       |

### 🔒 Authenticated User Routes

| Route                | Purpose                               |
|----------------------|----------------------------------------|
| `/events`            | View all community events             |
| `/rsvp`              | RSVP to an event                      |
| `/chat`              | Access group chat interface           |
| `/groups`            | View/join interest groups             |
| `/account`           | Manage account details                |
| `/notifications`     | View system messages/reminders        |
| `/feedback`          | Submit user feedback                  |
| `/booking`           | Start booking process                 |
| `/booking/select`    | Pick booking time/date/location       |
| `/booking/manage`    | Manage or cancel existing bookings    |
| `/logout`            | Log out of session                    |

---

## 🔐 Security Implementation

SeniorConnect is built with security in mind, following OWASP Top 10 practices:

| OWASP 2021 Risk                       | Implementation                                               |
|--------------------------------------|--------------------------------------------------------------|
| A01: Broken Access Control           | `@login_required`, role-based access planned                 |
| A02: Cryptographic Failures          | `.env` for secrets, Bcrypt hashing, HTTPS-ready              |
| A03: Injection                       | SQLAlchemy & parameterized queries                           |
| A04: Insecure Design                 | Future role-based logic                                      |
| A05: Security Misconfiguration       | Flask-Limiter, `debug=False` in production                   |
| A07: Identification and Authentication Failures | Flask-Login + Flask-Bcrypt                     |
| A08: Software and Data Integrity Failures | Secure deserialization planned for forms           |
| A09: Security Logging and Monitoring Failures | Python `logging` module planned                    |

---

## 🚀 Getting Started

### 📦 Installation

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
    ```

5. Import the schema:
    ```sql
    SOURCE db/schema.sql;
    SOURCE db/seed_data.sql;
    ```

### 🧪 Run the App

```bash
python app.py
```

This will launch the Flask server using the `create_app()` pattern.

---

## 📌 Completed Milestones

- ✅ MySQL-backed login and user registration
- ✅ Secure password hashing with Bcrypt
- ✅ Blueprinted user routes and session management
- ⏳ Role-based access for admins vs seniors (planned)
- ⏳ Full calendar view for booking (planned)

---

## 👨‍💻 Authors

- Hans Morillo

---

## 📄 License

This project is intended for academic purposes and follows the submission guidelines for the Application Security Project IT2555.
