import requests
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user


def get_weather_data(city="Singapore", api_key="42ba2a40d942a74fc7ad6b9bf7fc8c3f"):
    """Fetch weather data from OpenWeatherMap API"""
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
            # Process current weather (unchanged)
            weather_info = {
                'city': current_data['name'],
                'country': current_data['sys']['country'],
                'temperature': round(current_data['main']['temp']),
                'feels_like': round(current_data['main']['feels_like']),
                'humidity': current_data['main']['humidity'],
                'pressure': current_data['main']['pressure'],
                'description': current_data['weather'][0]['description'].title(),
                'icon': current_data['weather'][0]['icon'],
                'wind_speed': round(current_data['wind']['speed'] * 3.6, 1),
                'visibility': current_data.get('visibility', 0) / 1000,
                'sunrise': datetime.fromtimestamp(current_data['sys']['sunrise']).strftime('%I:%M %p'),
                'sunset': datetime.fromtimestamp(current_data['sys']['sunset']).strftime('%I:%M %p'),
                'current_time': datetime.now().strftime('%A, %B %d, %Y at %I:%M %p'),
                'uv_index': get_uv_advice(current_data['main']['temp']),
                'health_advice': get_health_advice(current_data['main']['temp'], current_data['main']['humidity'])
            }
            
            # Process 5-day forecast - NEW IMPROVED VERSION
            daily_forecasts = []
            forecasts_by_date = {}

            # Group all forecasts by date
            for item in forecast_data['list']:
                forecast_date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                if forecast_date not in forecasts_by_date:
                    forecasts_by_date[forecast_date] = []
                forecasts_by_date[forecast_date].append(item)

            # Get the next 5 days (including today)
            next_5_days = sorted(forecasts_by_date.keys())[:5]

            for date in next_5_days:
                day_forecasts = forecasts_by_date[date]
                
                # Get ALL temperature values for the day
                all_temps = [f['main']['temp'] for f in day_forecasts]
                temp_min = round(min(all_temps))
                temp_max = round(max(all_temps))
                
                # Get a representative forecast for midday (12pm) if available
                representative_forecast = None
                for f in day_forecasts:
                    forecast_hour = datetime.fromtimestamp(f['dt']).hour
                    if forecast_hour == 12:  # Prefer noon forecast
                        representative_forecast = f
                        break
                
                # Fallback to first forecast if no midday forecast found
                if not representative_forecast:
                    representative_forecast = day_forecasts[len(day_forecasts)//2]  # middle forecast
                
                # Format the date nicely (e.g., "Thursday, Aug 06")
                formatted_date = datetime.fromtimestamp(representative_forecast['dt']).strftime('%A, %b %d')
                
                daily_forecasts.append({
                    'date': formatted_date,
                    'temp_max': temp_max,
                    'temp_min': temp_min,
                    'description': representative_forecast['weather'][0]['description'].title(),
                    'icon': representative_forecast['weather'][0]['icon'],
                    'humidity': representative_forecast['main']['humidity']
                })

            weather_info['forecast'] = daily_forecasts
            return weather_info
            
        else:
            return {'error': 'Unable to fetch weather data'}
            
    except Exception as e:
        return {'error': f'Weather service unavailable: {str(e)}'}

def get_health_advice(temp, humidity):
    """Provide health advice based on weather conditions for seniors"""
    advice = []
    
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
    if temp > 28:
        return "High UV expected - Use SPF 30+ sunscreen"
    elif temp > 22:
        return "Moderate UV - Light sun protection recommended"
    else:
        return "Low UV conditions"

# Weather functions for SeniorConnect
def weather_page():
    """Weather page route - integrates with existing Flask app"""
    city = request.args.get('city', 'Singapore')  # Default to Singapore
    weather_data = get_weather_data(city)
    
    if 'error' in weather_data:
        flash(f'Weather Error: {weather_data["error"]}', 'danger')
        return render_template('weather.html', error=weather_data['error'], city=city)
    
    return render_template('weather.html', weather=weather_data, city=city)

# API endpoint for AJAX updates
def weather_api():
    """API endpoint for getting weather data as JSON"""
    city = request.args.get('city', 'Singapore')
    weather_data = get_weather_data(city)
    return jsonify(weather_data)