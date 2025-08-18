from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField, SelectField, RadioField, HiddenField
from wtforms.validators import DataRequired, Email, NumberRange, Length, Optional

class BookingForm(FlaskForm):
    # Event Info
    location = HiddenField('Location', validators=[DataRequired()])
    date = HiddenField('Date', validators=[DataRequired()])
    start_time = HiddenField('Start Time', validators=[DataRequired()])
    end_time = HiddenField('End Time', validators=[DataRequired()])
    title = StringField('Event Title', validators=[DataRequired(), Length(min=3, max=50)])
    interest_group = SelectField('Interest Group', choices=[
        ('Yoga', 'Yoga'), ('Chess', 'Chess'), ('Taichi', 'Taichi'), 
        ('Mahjong', 'Mahjong'), ('Gardening', 'Gardening')
    ], validators=[DataRequired()])
    attendees = IntegerField('Expected Number of Attendees', validators=[DataRequired(), NumberRange(min=1)])
    activity_type = SelectField('Activity Type', choices=[
        ('Workshop', 'Workshop'), ('Talk', 'Talk'), ('Performance', 'Performance'),
        ('Hands-on Session', 'Hands-on Session'), ('Meeting', 'Meeting'), 
        ('Event', 'Event'), ('Others', 'Others')
    ], validators=[DataRequired()])
    equipment = TextAreaField('Equipment Required', validators=[Optional(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])

    # Organiser Info
    organiser_name = StringField('Organiser Name', validators=[DataRequired()])
    organiser_email = StringField('Organiser Email', validators=[DataRequired(), Email()])
    organiser_contact = StringField('Organiser Phone', validators=[DataRequired(), Length(min=8, max=8)])
    accessibility_help = RadioField('Accessibility Help', choices=[('Yes', 'Yes'), ('No', 'No')], validators=[DataRequired()])
