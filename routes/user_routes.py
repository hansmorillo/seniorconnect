# user_routes.py - Updated with admin decorator
from dotenv import load_dotenv
load_dotenv()

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
import requests
from models.feedback import Feedback
from flask_login import login_required, current_user
from extensions import db, limiter  # 🔒 ONLY import db here, NOT limiter
import uuid
from datetime import datetime, timedelta
from models.notifications import Notification 
import os
from utils.security_utils import sanitize_input
from flask_limiter.util import get_remote_address
from functools import wraps

user = Blueprint('user', __name__)

# 🔒 ADMIN DECORATOR
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

# 🔒 HELPER FUNCTION to get limiter (avoids circular import)
def get_limiter():
    """Get limiter instance - avoids circular import issues"""
    from extensions import limiter
    return limiter

# 🔒 RATE LIMITING KEY FUNCTIONS
def get_user_id():
    """Get user ID for authenticated users, IP for anonymous"""
    if current_user and current_user.is_authenticated:
        return f"user:{current_user.id}"
    return f"ip:{get_remote_address()}"

def get_user_and_ip():
    """Combination key for strict rate limiting"""
    user_part = f"user:{current_user.id}" if current_user and current_user.is_authenticated else "anonymous"
    ip_part = f"ip:{get_remote_address()}"
    return f"{user_part}:{ip_part}"

# 🔒 NOTIFICATION ROUTES WITH RATE LIMITING
@user.route('/notifications')
@login_required
def notifications():
    """
    Display all notifications for the current user
    Security: Only shows notifications belonging to the logged-in user
    Rate Limited: Applied via get_limiter() function
    """
    # Apply rate limiting dynamically
    limiter = get_limiter()
    if limiter:
        # Check rate limit manually
        try:
            limiter.check()
        except Exception:
            # Rate limit exceeded, return 429
            return render_template('errors/rate_limit_exceeded.html', 
                                 description="Too many notification requests"), 429
    
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()
    
    return render_template('notifications.html', notifications=notifications)

@user.route('/notifications/<notification_id>/dismiss', methods=['POST'])
@login_required
def dismiss_notification(notification_id):
    """
    Delete a specific notification
    Security: Ensures user can only delete their own notifications
    """
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        print(f"SECURITY WARNING: User {current_user.id} tried to delete notification {notification_id} owned by {notification.user_id}")
        abort(403)
        
    db.session.delete(notification)
    db.session.commit()
    flash('Notification dismissed!', 'notification_success')
    return redirect(url_for('user.notifications'))

@user.route('/notifications/mark-all-read', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def mark_all_notifications_read():
    """
    Mark all notifications as read for the current user
    Security: Only affects notifications belonging to the logged-in user
    """
    try:
        # Update all notifications for the current user to mark as read
        updated_count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        if updated_count > 0:
            flash(f'{updated_count} notifications marked as read!', 'success')
        else:
            flash('No unread notifications to mark as read.', 'info')
            
    except Exception as e:
        db.session.rollback()
        print(f"Error marking all notifications as read: {str(e)}")
        flash('Error marking notifications as read. Please try again.', 'danger')
    
    return redirect(url_for('user.notifications'))

@user.route('/notifications/clear-all', methods=['POST'])
@login_required
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def clear_all_notifications():
    """
    Delete all notifications for the current user
    Security: Only deletes notifications belonging to the logged-in user
    """
    try:
        # Delete all notifications for the current user
        deleted_count = Notification.query.filter_by(
            user_id=current_user.id
        ).delete()
        
        db.session.commit()
        
        if deleted_count > 0:
            flash(f'{deleted_count} notifications cleared!', 'success')
        else:
            flash('No notifications to clear.', 'info')
            
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing all notifications: {str(e)}")
        flash('Error clearing notifications. Please try again.', 'danger')
    
    return redirect(url_for('user.notifications'))

@user.route('/account')
@login_required
def account_settings():
    return render_template('account.html')

# 🔒 FEEDBACK ROUTES WITH MANUAL RATE LIMITING CHECK
@user.route('/feedback', methods=['GET', 'POST'])
@login_required
@limiter.limit("5 per minute")  # Throttle brute-force attempts
def feedback():
    """
    Handle user feedback submission
    Security: Input sanitization for user-generated content
    Rate Limited: Manual check to avoid circular import
    """
    # Manual rate limiting check
    limiter = get_limiter()
    if limiter and request.method == 'POST':
        try:
            # Check if user has exceeded rate limit for feedback
            key = get_user_id()
            # This is a simplified check - in production you'd want more sophisticated logic
            pass  # Let the request proceed for now
        except Exception as e:
            return render_template('errors/rate_limit_exceeded.html', 
                                 description="Too many feedback submissions"), 429
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        if not subject or not content:
            flash('Both subject and content are required', 'danger')
            return redirect(url_for('user.feedback'))

        try:
            # 🔒 Sanitize inputs to prevent XSS
            sanitized_subject = sanitize_input(subject)
            sanitized_content = sanitize_input(content)
            
            new_feedback = Feedback(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                name=current_user.display_name,
                email=current_user.email,
                subject=sanitized_subject,
                content=sanitized_content
            )
            db.session.add(new_feedback)
            db.session.commit()
            
            # 🔒 Log successful feedback submission
            print(f"✅ FEEDBACK SUBMITTED: User {current_user.id} - Subject: {sanitized_subject[:50]}...")
            
            flash('Your feedback has been submitted successfully!', 'success')
            return redirect(url_for('user.feedback'))
            
        except Exception as e:
            db.session.rollback()
            print("="*50)
            print("FEEDBACK SUBMISSION ERROR DETAILS:")
            print(f"Error Type: {type(e)}")
            print(f"Error Message: {str(e)}")
            print("Form Data:", request.form)
            print("User:", current_user.id, current_user.email)
            print("="*50)
            
            flash(f'Error submitting feedback: {str(e)}', 'danger')
    
    return render_template('feedback.html')

@user.route('/feedback-display')
@login_required
@admin_required
def feedback_display():
    """
    Display feedback with pagination - ADMIN ONLY
    Security: All displayed content should be sanitized when stored
    """
    page = request.args.get('page', 1, type=int)
    feedback_pagination = Feedback.query.order_by(
        Feedback.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('feedback_display.html', 
                         feedback=feedback_pagination,
                         feedback_list=feedback_pagination.items)

@user.route('/feedback/<feedback_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_feedback(feedback_id):
    """
    Delete a specific feedback entry - ADMIN ONLY
    Security: Only admins can delete feedback
    """
    try:
        # Get the feedback entry
        feedback_entry = Feedback.query.get_or_404(feedback_id)
        
        # Delete the feedback
        db.session.delete(feedback_entry)
        db.session.commit()
        
        print(f"✅ FEEDBACK DELETED: Admin {current_user.id} deleted feedback {feedback_id}")
        flash('Feedback deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting feedback: {str(e)}")
        flash('Error deleting feedback. Please try again.', 'danger')
    
    return redirect(url_for('user.feedback_display'))

# 🔒 WEATHER ROUTES
@user.route('/weather')
@login_required
@limiter.limit("10 per minute")  # Throttle brute-force attempts
def weather():
    """Weather dashboard"""
    weather_data = get_weather_data()
    
    if 'error' in weather_data:
        flash(f'Weather Error: {weather_data["error"]}', 'danger')
        return render_template('weather.html', error=weather_data['error'])
    
    return render_template('weather.html', weather=weather_data)

@user.route('/weather-api')
@login_required 
def weather_api():
    """API endpoint for AJAX weather updates - Singapore only"""
    weather_data = get_weather_data()
    return jsonify(weather_data)

@user.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    return render_template('dashboard.html')

# 🔒 WEATHER API FUNCTION
def get_weather_data():
    """
    Fetch weather data from OpenWeatherMap API for Singapore only
    🔒 SECURITY: API key retrieved from environment variables
    """
    api_key = os.getenv('OPEN_WEATHER')
    
    if not api_key:
        return {'error': 'Weather service configuration error'}
    
    city = "Singapore"  # Fixed to Singapore - no user input
    
    try:
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        
        current_response = requests.get(current_url, timeout=10)
        forecast_response = requests.get(forecast_url, timeout=10)
        
        if current_response.status_code == 200 and forecast_response.status_code == 200:
            current_data = current_response.json()
            forecast_data = forecast_response.json()
            
            if not current_data.get('main') or not forecast_data.get('list'):
                return {'error': 'Invalid weather data received'}
            
            weather_info = {
                'city': str(current_data.get('name', 'Singapore'))[:50],
                'country': str(current_data.get('sys', {}).get('country', 'SG'))[:10],
                'temperature': round(float(current_data['main'].get('temp', 0))),
                'feels_like': round(float(current_data['main'].get('feels_like', 0))),
                'humidity': int(current_data['main'].get('humidity', 0)),
                'pressure': int(current_data['main'].get('pressure', 0)),
                'description': str(current_data.get('weather', [{}])[0].get('description', 'Unknown')).title()[:100],
                'icon': str(current_data.get('weather', [{}])[0].get('icon', '01d'))[:10],
                'wind_speed': round(float(current_data.get('wind', {}).get('speed', 0)) * 3.6, 1),
                'visibility': float(current_data.get('visibility', 10000)) / 1000,
                'sunrise': datetime.fromtimestamp(int(current_data.get('sys', {}).get('sunrise', 0))).strftime('%I:%M %p') if current_data.get('sys', {}).get('sunrise') else 'N/A',
                'sunset': datetime.fromtimestamp(int(current_data.get('sys', {}).get('sunset', 0))).strftime('%I:%M %p') if current_data.get('sys', {}).get('sunset') else 'N/A',
                'current_time': datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'),
                'uv_index': get_uv_advice(current_data['main'].get('temp', 0)),
                'health_advice': get_health_advice(current_data['main'].get('temp', 0), current_data['main'].get('humidity', 0))
            }
            
            # Process 5-day forecast
            daily_forecasts = []
            processed_dates = set()
            
            for item in forecast_data.get('list', []):
                if not item.get('dt') or not item.get('main'):
                    continue
                    
                try:
                    forecast_date = datetime.fromtimestamp(int(item['dt'])).date()
                    forecast_hour = datetime.fromtimestamp(int(item['dt'])).hour
                    
                    if forecast_date not in processed_dates and 11 <= forecast_hour <= 14:
                        daily_forecasts.append({
                            'date': datetime.fromtimestamp(int(item['dt'])).strftime('%A, %b %d'),
                            'temp_max': round(float(item['main'].get('temp_max', 0))),
                            'temp_min': round(float(item['main'].get('temp_min', 0))),
                            'description': str(item.get('weather', [{}])[0].get('description', 'Unknown')).title()[:100],
                            'icon': str(item.get('weather', [{}])[0].get('icon', '01d'))[:10],
                            'humidity': int(item['main'].get('humidity', 0))
                        })
                        processed_dates.add(forecast_date)
                        
                        if len(daily_forecasts) >= 5:
                            break
                except (ValueError, TypeError, KeyError):
                    continue
            
            weather_info['forecast'] = daily_forecasts
            return weather_info
            
        else:
            return {'error': 'Unable to fetch weather data. Please try again later.'}
            
    except requests.exceptions.Timeout:
        return {'error': 'Weather service timeout - please try again'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Weather service unavailable - please check your connection'}
    except ValueError:
        return {'error': 'Invalid weather data format received'}
    except Exception as e:
        print(f"Weather API Error: {str(e)}")
        return {'error': 'Weather service temporarily unavailable'}

def get_health_advice(temp, humidity):
    """Provide health advice based on weather conditions for seniors in Singapore"""
    advice = []
    
    try:
        temp = float(temp) if temp is not None else 25
        humidity = float(humidity) if humidity is not None else 50
    except (ValueError, TypeError):
        temp, humidity = 25, 50
    
    if temp > 32:
        advice.append("Very hot day - Stay indoors with air conditioning during peak hours")
        advice.append("Drink plenty of water and wear light, breathable clothing")
    elif temp > 28:
        advice.append("Warm day - Perfect for early morning or evening outdoor activities")
        advice.append("Don't forget sunscreen and stay hydrated")
    elif temp > 24:
        advice.append("Pleasant weather - Great for outdoor walks and activities")
        advice.append("Light sun protection recommended")
    else:
        advice.append("Cooler day - Comfortable for all outdoor activities")
    
    if humidity > 85:
        advice.append("Very high humidity - Take frequent breaks and stay cool")
    elif humidity > 70:
        advice.append("High humidity typical for Singapore - Stay hydrated")
    
    return advice

def get_uv_advice(temp):
    """UV advice for Singapore's tropical climate"""
    try:
        temp = float(temp) if temp is not None else 25
    except (ValueError, TypeError):
        temp = 25
        
    if temp > 30:
        return "High UV expected - Use SPF 50+ sunscreen and seek shade"
    elif temp > 26:
        return "Moderate to high UV - SPF 30+ sunscreen recommended"
    else:
        return "Moderate UV conditions - Light sun protection advised"