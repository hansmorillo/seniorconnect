from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, abort
import requests
from models.feedback import Feedback
from flask_login import login_required, current_user
from extensions import db
import uuid
from datetime import datetime, timedelta
from models.notifications import Notification 

user = Blueprint('user', __name__)

@user.route('/notifications')
@login_required
def notifications():
    # Only queries notifications for current_user.id
    notifications = Notification.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Notification.created_at.desc()
    ).all()
    
    return render_template('notifications.html', notifications=notifications)

@user.route('/create-test-notifications')
@login_required
def create_test_notifs():
    test_notif = Notification(
        id=str(uuid.uuid4()),
        user_id=current_user.id, # Always tied to current user
        type='test',
        message='Test notification',
        event_name='Sample Event',
        date_time='2023-01-01 12:00',
        location='Test Location',
        comments='Test comment'
    )
    db.session.add(test_notif)
    db.session.commit()
    return "Created test notification"

@user.route('/notifications/<notification_id>/dismiss', methods=['POST'])
@login_required
def dismiss_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    # CRITICAL SECURITY CHECK: Ensure the notification belongs to current user
    if notification.user_id != current_user.id:
        abort(403) # Forbidden if trying to dismiss someone else's notification
        
    db.session.delete(notification)
    db.session.commit()
    flash('Notification dismissed!', 'notification_success')  # Changed category
    return redirect(url_for('user.notifications'))

@user.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    # Only updates notifications for current_user.id
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read!', 'notification_success')  # Changed category
    return redirect(url_for('user.notifications'))

@user.route('/notifications/clear-all', methods=['POST'])
@login_required
def clear_all_notifications():
    # Only deletes notifications for current_user.id
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('All notifications cleared!', 'notification_success')  # Changed category
    return redirect(url_for('user.notifications'))

@user.route('/account')
@login_required
def account_settings():
    return render_template('account.html')

@user.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        subject = request.form.get('subject')
        content = request.form.get('content')
        
        if not subject or not content:
            flash('Both subject and content are required', 'danger')
            return redirect(url_for('user.feedback'))

        try:
            new_feedback = Feedback(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                name=current_user.display_name,
                email=current_user.email,
                subject=subject,
                content=content
            )
            db.session.add(new_feedback)
            db.session.commit()
            flash('Your feedback has been submitted successfully!', 'success')  # More specific message
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
def feedback_display():
    # Pagination implementation
    page = request.args.get('page', 1, type=int)
    feedback_pagination = Feedback.query.order_by(
        Feedback.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('feedback_display.html', 
                         feedback=feedback_pagination,
                         feedback_list=feedback_pagination.items)  # Pass both pagination object and items

@user.route('/delete-feedback/<feedback_id>', methods=['POST'])
@login_required
def delete_feedback(feedback_id):
    feedback = Feedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    flash('Feedback deleted successfully', 'success')
    return redirect(url_for('user.feedback_display'))

# Weather routes - Singapore only
@user.route('/weather')
@login_required
def weather():
    weather_data = get_weather_data()  # Always Singapore
    
    if 'error' in weather_data:
        flash(f'Weather Error: {weather_data["error"]}', 'danger')
        return render_template('weather.html', error=weather_data['error'])
    
    return render_template('weather.html', weather=weather_data)

@user.route('/weather-api')
@login_required 
def weather_api():
    """API endpoint for AJAX weather updates - Singapore only"""
    weather_data = get_weather_data()  # Always Singapore
    return jsonify(weather_data)

# Weather functionality - Singapore only
def get_weather_data(api_key="42ba2a40d942a74fc7ad6b9bf7fc8c3f"):
    """
    Fetch weather data from OpenWeatherMap API for Singapore only
    Returns formatted weather information suitable for seniors
    """
    city = "Singapore"  # Fixed to Singapore
    
    try:
        # Current weather endpoint
        current_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        
        # 5-day forecast endpoint
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        
        # Fetch current weather
        current_response = requests.get(current_url)
        current_data = current_response.json()
        
        # Fetch forecast
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()
        
        if current_response.status_code == 200 and forecast_response.status_code == 200:
            # Process current weather
            weather_info = {
                'city': current_data['name'],
                'country': current_data['sys']['country'],
                'temperature': round(current_data['main']['temp']),
                'feels_like': round(current_data['main']['feels_like']),
                'humidity': current_data['main']['humidity'],
                'pressure': current_data['main']['pressure'],
                'description': current_data['weather'][0]['description'].title(),
                'icon': current_data['weather'][0]['icon'],
                'wind_speed': round(current_data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                'visibility': current_data.get('visibility', 0) / 1000,  # Convert to km
                'sunrise': datetime.fromtimestamp(current_data['sys']['sunrise']).strftime('%I:%M %p'),
                'sunset': datetime.fromtimestamp(current_data['sys']['sunset']).strftime('%I:%M %p'),
                'current_time': datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'),
                'uv_index': get_uv_advice(current_data['main']['temp']),
                'health_advice': get_health_advice(current_data['main']['temp'], current_data['main']['humidity'])
            }
            
            # Process 5-day forecast (take one reading per day around noon)
            daily_forecasts = []
            processed_dates = set()
            
            for item in forecast_data['list']:
                forecast_date = datetime.fromtimestamp(item['dt']).date()
                forecast_hour = datetime.fromtimestamp(item['dt']).hour
                
                # Take the forecast closest to noon for each day
                if forecast_date not in processed_dates and 11 <= forecast_hour <= 14:
                    daily_forecasts.append({
                        'date': datetime.fromtimestamp(item['dt']).strftime('%A, %b %d'),
                        'temp_max': round(item['main']['temp_max']),
                        'temp_min': round(item['main']['temp_min']),
                        'description': item['weather'][0]['description'].title(),
                        'icon': item['weather'][0]['icon'],
                        'humidity': item['main']['humidity']
                    })
                    processed_dates.add(forecast_date)
                    
                    if len(daily_forecasts) >= 5:
                        break
            
            weather_info['forecast'] = daily_forecasts
            return weather_info
            
        else:
            return {'error': 'Unable to fetch weather data for Singapore. Please try again later.'}
            
    except Exception as e:
        return {'error': f'Weather service unavailable: {str(e)}'}

def get_health_advice(temp, humidity):
    """Provide health advice based on weather conditions for seniors in Singapore"""
    advice = []
    
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
    if temp > 30:
        return "High UV expected - Use SPF 50+ sunscreen and seek shade"
    elif temp > 26:
        return "Moderate to high UV - SPF 30+ sunscreen recommended"
    else:
        return "Moderate UV conditions - Light sun protection advised"