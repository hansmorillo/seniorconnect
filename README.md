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
├── app.py                  # Main Flask app entry point
├── config.py               # Config variables (e.g., DB URI)
├── models/                 # ORM-like Python classes
├── routes/                 # All route Blueprints
├── templates/              # HTML templates with Jinja2
├── static/                 # CSS, images, scripts
├── utils/                  # Utility functions and helpers
├── db/                     # Optional scripts or migrations for DB setup
├── requirements.txt        # Python dependencies
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

| OWASP 2019 Risk               | Implementation                                               |
|------------------------------|--------------------------------------------------------------|
| A1: Injection                | Safe query handling via parameterized queries                |
| A2: Broken Authentication    | Flask-Login + Flask-Bcrypt                                   |
| A3: Sensitive Data Exposure  | `.env` files, Bcrypt hashing, HTTPS-ready                    |
| A5: Broken Access Control    | `@login_required`, role-based expansion planned              |
| A6: Security Misconfiguration| Flask-Limiter, `debug=False` in production                   |
| A8: Insecure Deserialization | JSON-safe deserialization planned for forms                  |
| A10: Insufficient Logging    | Python `logging` module support planned                      |

---

## 🚀 Getting Started

### 📦 Installation

1. Clone the repo:
    ```bash
    git clone xxx
    cd seniorconnect
    ```

2. Set up a virtual environment:
    ```bash
    python -m venv venv        # if python is not recognised ..., and PATH is installed correctly, run 'py -m venv venv' and use py for all further use
    source venv/bin/activate   # On Windows: venv\Scripts\activate
    ```

3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4. Create a `.env` file for secret keys and DB config (if applicable)

### 🧪 Run the App

```bash
python app.py                  # if python is not recognised ..., and PATH is installed correctly, run 'py -m venv venv' and use py for all further use 
```

---

## 📌 Future Work

- MySQL-backed login and user registration
- Role-based access for admins vs seniors
- Full calendar view for booking
- Real-time chat with WebSockets

---

## 👨‍💻 Authors

- Hans Morillo
- SeniorConnect Development Team

---

## 📄 License

This project is intended for academic purposes and follows the submission guidelines for the Application Security Project IT2555.
