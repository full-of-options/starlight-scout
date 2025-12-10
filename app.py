from flask import Flask, render_template, request, jsonify
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize Client
try:
    client = genai.Client(api_key=api_key)
except:
    client = None

app = Flask(__name__)

# --- 🛡️ MOCK DATA ---
MOCK_PLAN = {
  "summary": { "moon_phase": "Waxing Gibbous", "weather": "Clear (Simulated)", "score": 85, "strategy": "DEMO MODE: API Overloaded. Showing Example Plan." },
  "targets": [
    { "name": "M42", "type": "Nebula", "why": "Orion Nebula", "settings": { "exposure": "10s", "gain": "80", "filter": "Dual", "binning": "2x2", "ir_mode": "Astro" }, "tips": ["Short exposures."] },
    { "name": "M45", "type": "Cluster", "why": "Pleiades", "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" }, "tips": ["Watch halos."] }
  ],
  "events": []
}

def clean_json_text(text):
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != -1: return text[start:end]
    return text

def calculate_optics(equipment_name):
    specs = { "name": "Standard", "fov_val": 5.0, "icon": "📷" }
    if equipment_name:
        name = str(equipment_name).lower()
        if "dwarf" in name: specs = { "name": "Dwarf II", "fov_val": 3.0, "icon": "🔭" }
        elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    return specs

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = { "name": "Setup", "fov_val": 5.0, "icon": "📷" }
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        try:
            loc = request.form.get('location')
            eq = request.form.get('equipment')
            date = request.form.get('date')
            if eq: optics = calculate_optics(eq)

            if loc and eq:
                if not client: raise Exception("API Client Missing")
                
                # Using verified Lite model
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                    contents=f"Date: {date}. Loc: {loc}. Eq: {eq}. Output Strict JSON."
                )
                data = json.loads(clean_json_text(response.text))
                
        except Exception as e:
            print(f"API ERROR: {e}")
            data = MOCK_PLAN
            err_str = str(e)
            if "503" in err_str: error_msg = "Google AI is temporarily overloaded. Showing demo data."
            elif "429" in err_str: error_msg = "API quota exceeded. Showing demo data."
            else: error_msg = f"Connection issue. Showing demo data."
            data['error'] = error_msg

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        lat, lon = data.get('lat'), data.get('lon')
        
        if not client: raise Exception("No API")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Convert {lat},{lon} to 'City, State' only. No text."
        )
        text = response.text.strip()
        if "**" in text: text = text.split("**")[1]
        return jsonify({"location": text})
        
    except Exception:
        return jsonify({"location": f"{lat:.3f}, {lon:.3f}"})

if __name__ == '__main__':
    app.run(debug=True)