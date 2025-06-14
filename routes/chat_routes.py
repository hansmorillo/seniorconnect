from flask import Blueprint, render_template
from flask_login import login_required

chat = Blueprint('chat', __name__)

@chat.route('/chat')
@login_required
def chat_main():
    return render_template('chat.html')
