from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length

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
        validators=[DataRequired(), Email(message="Enter a valid email address")]
    )
    phone = StringField(
        'Phone Number',
        validators=[DataRequired(), Length(min=8, max=20)]
    )
    password = PasswordField(
        'Password',
        validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters")]
    )
    submit = SubmitField('Register')

