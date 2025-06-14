from flask import Blueprint, render_template
from flask_login import login_required

group = Blueprint('group', __name__)

@group.route('/groups')
@login_required
def view_groups():
    return render_template('interest_groups.html')

@group.route('/groups/join/<int:group_id>')
@login_required
def join_group(group_id):
    # Later: Add logic to join a group by ID
    return render_template('interest_groups.html')  # Placeholder
