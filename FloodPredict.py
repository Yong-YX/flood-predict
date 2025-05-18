from flask import Flask, render_template, request, jsonify
import requests
from collections import defaultdict

app = Flask(__name__, template_folder='facecover')

base_url2 = 'http://api.openweathermap.org/data/2.5/weather'
api_key2 = '6e6f9659fef62e5c5d1103979100d281'
api_key = '65af77cf9286fead9050d1ef1b8037ec'
base_url = 'https://api.openweathermap.org/data/2.5/forecast?'

def summarize_risk_level(forecast_list):
    risk_counts = {'High': 0, 'Moderate': 0, 'Low': 0}
    high_risk_times = []
    
    for entry in forecast_list:
        risk = entry['risk']
        risk_counts[risk] += 1
        if risk == 'High':
           high_risk_times.append(entry['time'])


    if high_risk_times:
        return f"High risk detected at: {', '.join(high_risk_times)}"
    majority_risk = max(risk_counts, key=risk_counts.get)
    return majority_risk


def assess_flood_risk(pop_value, sea_level, weather_main):
    if pop_value >= 0.8 and sea_level <= 1005 and weather_main in ['Rain', 'Thunderstorm']:
        return "High"
    elif pop_value >= 0.6 and sea_level <= 1008 and weather_main in ['Rain', 'Clouds']:
        return "Moderate"
    else:
        return "Low"
    
@app.route('/')
def index():
    return render_template('cover.html') 

from flask import redirect, url_for, session

@app.route('/forecast', methods=['POST'])
def forecast():
    city = request.form.get('city')
    session['city'] = city 
    return render_template('result.html')
    
def get_forecast_data(city):
    request_url2 = f"{base_url2}?appid={api_key2}&q={city}"
    response2 = requests.get(request_url2)

    if response2.status_code != 200:
        return None, "City not found"
    
    data2 = response2.json()
    lon = data2['coord']['lon']
    lat = data2['coord']['lat']
    temperature = float(data2['main']['temp'] - 273.15)
    rounded_temperature = round(temperature)
    weather_data = {
        'city': city,
        'temperature': rounded_temperature,
        'description': data2['weather'][0]['description'],
        'lat': lat,
        'lon': lon
    }

    forecast_url = f"{base_url}lat={lat}&lon={lon}&appid={api_key}&units=metric"
    forecast_response = requests.get(forecast_url)

    if forecast_response.status_code != 200:
        return None, "City not found"

    forecast_data = forecast_response.json()
    forecast_list = []
    high_risk_times = []

    for entry in forecast_data['list'][:24]:
        time = entry['dt_txt']
        pop_value = entry.get('pop', 0) 
        temperature1 = entry['main'].get('temp_max')
        sea_level = entry['main'].get('sea_level', 1010)
        weather_main = entry['weather'][0]['main']
        risk = assess_flood_risk(pop_value, sea_level, weather_main)

        forecast_entry = {
            'time': time,
            'pop': int(pop_value * 100),  
            'sea_level': sea_level,
            'temp' : temperature1,
            'weather': weather_main,
            'icon': entry['weather'][0]['icon'],
            'risk': risk
        }

        forecast_list.append(forecast_entry)

        if risk == "High":
            high_risk_times.append(time)

    return {
        'weather': weather_data,
        'forecast': forecast_list,
        'high_risk_times': high_risk_times
    }, None

daily_risk_summary = {}


@app.route('/result', methods=['GET', 'POST'])
def result():
    result = None
    weather_data = None
    forecast_list = []
    high_risk_times = []
    majority_risk = None

    if request.method == 'POST':
        city = request.form['city']
        data, error = get_forecast_data(city)
        if error:
            result = error
        else:
            weather_data = data['weather']
            forecast_list = data['forecast']
            high_risk_times = data['high_risk_times']
            result = f"Weather for {city}: {weather_data['temperature']}°C, {weather_data['description']}, {weather_data['lon']}, {weather_data['lat']}"
            majority_risk = summarize_risk_level(forecast_list)

    return render_template('result.html', 
                       result=result, 
                       weather_data=weather_data, 
                       forecast_list=forecast_list, 
                       high_risk_times=high_risk_times,
                       majority_risk=majority_risk)

@app.route('/api/forecast')
def api_forecast():
    city = request.args.get('city')
    if not city:
        return jsonify({'error': 'City parameter is required'}), 400

    data, error = get_forecast_data(city)
    if error:
        return jsonify({'error': error}), 404
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
