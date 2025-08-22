from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp, ValidationError
from models.user import User

class LoginForm(FlaskForm):
    email = StringField(
        "Email address",
        validators=[DataRequired(), Email(), Length(max=255)],
        filters=[lambda x: x.strip().lower() if isinstance(x, str) else x]        # trims spaces before validation
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)]
    )
    remember = BooleanField("Remember for 30 days")
    recaptcha = RecaptchaField()  # Added reCAPTCHA field
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    display_name = StringField(
        'Display Name',
        validators=[DataRequired(), Length(min=2, max=50)]
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(message="Enter a valid email address"), Length(max=120)]
    )
    phone = StringField(
        'Phone Number',
        validators=[
            DataRequired(), 
            Regexp(r'^[89]\d{3}(?: ?\d{4})$', message="8 digits starting with 8 or 9; space optional (e.g., 9123 4567).")
        ]
    )
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message="Password must be at least 8 characters long"),
        Regexp(
            r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]+$',
            message="Password must include upper, lower, number, and special character"
        )
    ])      # Password Security
    recaptcha = RecaptchaField()  # Added reCAPTCHA field
    submit = SubmitField('Register')

    def validate_email(self, email):
        """Custom validator to check if email already exists"""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Email already registered. Please choose a different one.')

    def validate_phone(self, phone):
        """Custom validator to check if phone already exists"""
        # Clean the phone number for comparison
        clean_phone = phone.data.replace(' ', '')
        user = User.query.filter_by(phone_number=clean_phone).first()
        if user:
            raise ValidationError('Phone number already registered. Please choose a different one.')

class LogoutForm(FlaskForm):
    # Field is optional; CSRF is what we need. A submit helps if you validate.
    submit = SubmitField("Logout")