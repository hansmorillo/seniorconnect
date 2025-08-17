# weather.py - SECURE VERSION
import requests
import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user


def get_weather_data(city="Singapore"):
    """Fetch weather data from OpenWeatherMap API - SECURE VERSION"""
    
    # 🔒 SECURITY FIX 1: Get API key from environment
    api_key = os.getenv('OPENWEATHER_KEY')
    
    # 🔒 SECURITY FIX 2: Validate API key exists
    if not api_key:
        return {'error': 'Weather service configuration error'}
    
    # 🔒 SECURITY FIX 3: Input validation for city name
    if not city or not isinstance(city, str):
        city = "Singapore"
    
    # Clean city name to prevent injection
    city = city.strip()[:50]  # Limit length
    if not city.replace(' ', '').replace('-', '').isalpha():
        city = "Singapore"  # Fallback for invalid characters
    
    try:
        # 🔒 SECURITY FIX 4: Use HTTPS (your URLs already do this)
        current_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        
        # 🔒 SECURITY FIX 5: Add timeout to prevent hanging requests
        current_response = requests.get(current_url, timeout=10)
        forecast_response = requests.get(forecast_url, timeout=10)
        
        # 🔒 SECURITY FIX 6: Validate response before processing
        if current_response.status_code == 200 and forecast_response.status_code == 200:
            current_data = current_response.json()
            forecast_data = forecast_response.json()
            
            # 🔒 SECURITY FIX 7: Validate data structure exists
            if not current_data.get('main') or not forecast_data.get('list'):
                return {'error': 'Invalid weather data received'}
            
            # Process current weather (your existing logic with validation)
            weather_info = {
                'city': str(current_data.get('name', 'Unknown'))[:50],
                'country': str(current_data.get('sys', {}).get('country', 'Unknown'))[:10],
                'temperature': round(float(current_data['main'].get('temp', 0))),
                'feels_like': round(float(current_data['main'].get('feels_like', 0))),
                'humidity': int(current_data['main'].get('humidity', 0)),
                'pressure': int(current_data['main'].get('pressure', 0)),
                'description': str(current_data.get('weather', [{}])[0].get('description', 'Unknown')).title()[:100],
                'icon': str(current_data.get('weather', [{}])[0].get('icon', '01d'))[:10],
                'wind_speed': round(float(current_data.get('wind', {}).get('speed', 0)) * 3.6, 1),
                'visibility': float(current_data.get('visibility', 0)) / 1000,
                'sunrise': datetime.fromtimestamp(int(current_data.get('sys', {}).get('sunrise', 0))).strftime('%I:%M %p'),
                'sunset': datetime.fromtimestamp(int(current_data.get('sys', {}).get('sunset', 0))).strftime('%I:%M %p'),
                'current_time': datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'),
                'uv_index': get_uv_advice(current_data['main'].get('temp', 0)),
                'health_advice': get_health_advice(current_data['main'].get('temp', 0), current_data['main'].get('humidity', 0))
            }
            
            # Process 5-day forecast with validation
            daily_forecasts = []
            forecasts_by_date = {}

            # Group all forecasts by date with validation
            for item in forecast_data.get('list', []):
                if not item.get('dt') or not item.get('main'):
                    continue  # Skip invalid entries
                    
                forecast_date = datetime.fromtimestamp(int(item['dt'])).strftime('%Y-%m-%d')
                if forecast_date not in forecasts_by_date:
                    forecasts_by_date[forecast_date] = []
                forecasts_by_date[forecast_date].append(item)

            # Get the next 5 days
            next_5_days = sorted(forecasts_by_date.keys())[:5]

            for date in next_5_days:
                day_forecasts = forecasts_by_date[date]
                
                # Validate and process temperatures
                all_temps = []
                for f in day_forecasts:
                    if f.get('main', {}).get('temp') is not None:
                        all_temps.append(float(f['main']['temp']))
                
                if not all_temps:
                    continue  # Skip if no valid temperatures
                
                temp_min = round(min(all_temps))
                temp_max = round(max(all_temps))
                
                # Get representative forecast
                representative_forecast = None
                for f in day_forecasts:
                    forecast_hour = datetime.fromtimestamp(int(f.get('dt', 0))).hour
                    if forecast_hour == 12:
                        representative_forecast = f
                        break
                
                if not representative_forecast:
                    representative_forecast = day_forecasts[len(day_forecasts)//2]
                
                # Validate representative forecast
                if not representative_forecast.get('dt') or not representative_forecast.get('weather'):
                    continue
                
                formatted_date = datetime.fromtimestamp(int(representative_forecast['dt'])).strftime('%A, %b %d')
                
                daily_forecasts.append({
                    'date': str(formatted_date)[:50],
                    'temp_max': temp_max,
                    'temp_min': temp_min,
                    'description': str(representative_forecast.get('weather', [{}])[0].get('description', 'Unknown')).title()[:100],
                    'icon': str(representative_forecast.get('weather', [{}])[0].get('icon', '01d'))[:10],
                    'humidity': int(representative_forecast.get('main', {}).get('humidity', 0))
                })

            weather_info['forecast'] = daily_forecasts
            return weather_info
            
        else:
            # 🔒 SECURITY FIX 8: Don't expose detailed API errors to users
            return {'error': 'Unable to fetch weather data'}
            
    except requests.exceptions.Timeout:
        return {'error': 'Weather service timeout - please try again'}
    except requests.exceptions.ConnectionError:
        return {'error': 'Weather service unavailable - please check your connection'}
    except ValueError as e:
        # JSON decode errors
        return {'error': 'Invalid weather data format received'}
    except Exception as e:
        # 🔒 SECURITY FIX 9: Log error details server-side, show generic message to user
        print(f"Weather API Error: {str(e)}")  # Log for debugging
        return {'error': 'Weather service temporarily unavailable'}

def get_health_advice(temp, humidity):
    """Provide health advice based on weather conditions for seniors"""
    advice = []
    
    # 🔒 SECURITY FIX 10: Validate numeric inputs
    try:
        temp = float(temp) if temp is not None else 25
        humidity = float(humidity) if humidity is not None else 50
    except (ValueError, TypeError):
        temp, humidity = 25, 50  # Safe defaults
    
    if temp > 30:
        advice.append("🌡️ Very warm day - Stay hydrated and avoid prolonged sun exposure")
        advice.append("🏠 Consider staying indoors during peak hours (11am-3pm)")
    elif temp > 25:
        advice.append("☀️ Pleasant warm weather - Perfect for outdoor activities")
        advice.append("🧴 Don't forget sunscreen if going outside")
    elif temp < 18:
        advice.append("🧥 Cool day - Dress warmly in layers")
        advice.append("🏠 Great weather for indoor activities")
    else:
        advice.append("🌤️ Comfortable temperature for outdoor walks")
    
    if humidity > 80:
        advice.append("💧 High humidity - Take breaks if feeling uncomfortable")
    elif humidity < 30:
        advice.append("🌵 Low humidity - Stay hydrated and use moisturizer")
    
    return advice

def get_uv_advice(temp):
    """Simple UV advice based on temperature"""
    try:
        temp = float(temp) if temp is not None else 25
    except (ValueError, TypeError):
        temp = 25
        
    if temp > 28:
        return "High UV expected - Use SPF 30+ sunscreen"
    elif temp > 22:
        return "Moderate UV - Light sun protection recommended"
    else:
        return "Low UV conditions"

# 🔒 SECURITY FIX 11: Rate limiting helper (optional)
from functools import wraps
from time import time
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
api_calls = defaultdict(list)

def rate_limit(max_calls=10, window=60):
    """Rate limiting decorator for API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = getattr(current_user, 'id', 'anonymous') if current_user.is_authenticated else 'anonymous'
            now = time()
            
            # Clean old entries
            api_calls[user_id] = [call_time for call_time in api_calls[user_id] if now - call_time < window]
            
            # Check rate limit
            if len(api_calls[user_id]) >= max_calls:
                return {'error': 'Too many weather requests. Please wait a moment.'}
            
            # Record this call
            api_calls[user_id].append(now)
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Weather functions for SeniorConnect
@rate_limit(max_calls=5, window=60)  # 5 calls per minute
def weather_page():
    """Weather page route - integrates with existing Flask app"""
    # Singapore only - no user input for city
    weather_data = get_weather_data("Singapore")
    
    if 'error' in weather_data:
        flash(f'Weather Error: {weather_data["error"]}', 'danger')
        return render_template('weather.html', error=weather_data['error'])
    
    return render_template('weather.html', weather=weather_data)

# API endpoint for AJAX updates
@rate_limit(max_calls=10, window=60)  # 10 calls per minute for AJAX
def weather_api():
    """API endpoint for getting weather data as JSON"""
    weather_data = get_weather_data("Singapore")
    return jsonify(weather_data)