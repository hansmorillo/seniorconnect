from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp

class LoginForm(FlaskForm):
    email = StringField(
        'Email',
        validators=[DataRequired(), Email(message="Enter a valid email address")]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters")]
    )
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


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
            Regexp(
            r'^[89]\d{7}$',  # starts with 8 or 9 + 7 more digits
            message="Phone number must be 8 digits starting with 8 or 9, no space."
            )
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
    submit = SubmitField('Register')

