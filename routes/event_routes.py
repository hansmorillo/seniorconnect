from flask import Blueprint, render_template
from flask_login import login_required

event = Blueprint('event', __name__)

@event.route('/events')
@login_required
def events():
    return render_template('events.html')

@event.route('/rsvp')
@login_required
def rsvp():
    return render_template('rsvp.html')
