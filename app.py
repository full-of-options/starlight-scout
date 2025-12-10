from flask import Flask, render_template, request, jsonify
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"CLIENT ERROR: {e}")
    client = None

app = Flask(__name__)

# --- 🛡️ MOCK DATA ---
MOCK_PLAN = {
  "summary": { "moon_phase": "Waxing Gibbous", "weather": "Clear (Simulated)", "score": 85, "strategy": "DEMO MODE: Showing Example Data." },
  "targets": [
    { "name": "M42", "type": "Nebula", "why": "Orion Nebula", "settings": { "exposure": "10s", "gain": "80", "filter": "Dual", "binning": "2x2", "ir_mode": "Astro" }, "tips": ["Short exposures."] },
    { "name": "M45", "type": "Cluster", "why": "Pleiades", "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" }, "tips": ["Watch halos."] }
  ],
  "events": []
}

def clean_json_text(text):
    text = text.strip()
    start = text.find('{')
    list_start = text.find('[')
    
    if list_start != -1 and (start == -1 or list_start < start):
        end = text.rfind(']') + 1
        return text[list_start:end]
    
    end = text.rfind('}') + 1
    if start != -1 and end != -1: return text[start:end]
    return text

def normalize_data(data):
    if not data: return MOCK_PLAN
    if isinstance(data, list):
        return {
            "summary": { "moon_phase": "Unknown", "weather": "Clear", "score": 50, "strategy": "Standard Plan" },
            "targets": data,
            "events": []
        }
    if 'targets' not in data:
        for key in data:
            if isinstance(data[key], list) and len(data[key]) > 0:
                data['targets'] = data[key]
                break
    if 'summary' not in data:
        data['summary'] = { "moon_phase": "Unknown", "weather": "Clear", "score": 50, "strategy": "Standard Plan" }
    return data

def calculate_optics(equipment_name):
    specs = { "name": "Standard Setup", "fov_val": 5.0, "icon": "📷" }
    if equipment_name:
        name = str(equipment_name).lower()
        if "dwarf" in name: specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
        elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    return specs

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = { "name": "Setup", "fov_val": 5.0, "icon": "📷" }
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        loc = request.form.get('location')
        eq = request.form.get('equipment')
        date = request.form.get('date')
        if eq: optics = calculate_optics(eq)

        if not loc or not eq:
            data = MOCK_PLAN
            data['error'] = f"Missing Input! Loc: '{loc}', Eq: '{eq}'"
        else:
            try:
                if not client: raise Exception("API Client Failed")
                
                # SWITCHED TO STANDARD 2.0 (Fresh Quota)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                    contents=f"Date: {date}. Loc: {loc}. Eq: {eq}. Output JSON with keys: summary, targets, events."
                )
                
                try:
                    cleaned = clean_json_text(response.text)
                    raw_data = json.loads(cleaned)
                    data = normalize_data(raw_data)
                except json.JSONDecodeError:
                    raise Exception("AI returned bad JSON")
                
            except Exception as e:
                print(f"CRASH: {e}")
                data = MOCK_PLAN
                data['error'] = f"System Error: {str(e)}"

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        lat, lon = data.get('lat'), data.get('lon')
        if not client: return jsonify({"location": f"{lat:.3f}, {lon:.3f}"})
        
        try:
            # SWITCHED TO STANDARD 2.0 (Fresh Quota)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Convert {lat},{lon} to 'City, State' only. No text."
            )
            text = response.text.strip()
            if "**" in text: text = text.split("**")[1]
            return jsonify({"location": text})
        except:
            # BUG FIX: Return coords instead of "Location Found" text
            return jsonify({"location": f"{lat:.3f}, {lon:.3f}"})
            
    except:
        return jsonify({"location": "Error"})

if __name__ == '__main__':
    app.run(debug=True)