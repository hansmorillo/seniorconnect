from flask import Blueprint, render_template
from flask_login import login_required

user = Blueprint('user', __name__)

@user.route('/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

@user.route('/account')
@login_required
def account_settings():
    return render_template('account.html')

@user.route('/feedback')
@login_required
def feedback():
    return render_template('feedback.html')
