from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """
    Decorator to require admin privileges for a route
    Usage: @admin_required (place after @login_required)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)  # Unauthorized
        if not getattr(current_user, 'is_admin', False):
            abort(403)  # Forbidden
        return f(*args, **kwargs)
    return decorated_function