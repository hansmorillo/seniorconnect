from flask import Blueprint, render_template
from flask_login import login_required

booking = Blueprint('booking', __name__)

@booking.route('/booking')
# @login_required
def booking_main():
    return render_template('booking.html')

@booking.route('/booking/select')
@login_required
def booking_select():
    return render_template('booking_select.html')

@booking.route('/booking/manage')
@login_required
def booking_manage():
    return render_template('booking_manage.html')
