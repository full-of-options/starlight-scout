from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

try:
    client = genai.Client(api_key=api_key)
except:
    client = None

app = Flask(__name__)

MOCK_PLAN = {
  "summary": { "moon_phase": "Waxing Gibbous", "weather": "Clear", "score": 85, "strategy": "DEMO MODE" },
  "targets": [
    { "name": "M42", "type": "Nebula", "why": "Orion Nebula", "settings": { "exposure": "10s", "gain": "80", "filter": "Dual", "binning": "2x2", "ir_mode": "Astro" }, "tips": ["Tip 1"] },
    { "name": "M45", "type": "Cluster", "why": "Pleiades", "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" }, "tips": ["Tip 1"] }
  ],
  "events": []
}

def calculate_optics(equipment_name):
    # Safe Fallback
    specs = { "name": "Standard", "fov_val": 5.0, "icon": "📷" }
    if equipment_name:
        name = str(equipment_name).lower()
        if "dwarf" in name: specs = { "name": "Dwarf II", "fov_val": 3.0, "icon": "🔭" }
        elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    return specs

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    # 1. Init Optics to Safe Default
    optics = { "name": "Setup", "fov_val": 5.0, "icon": "📷" }
    
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        try:
            loc = request.form.get('location')
            eq = request.form.get('equipment')
            date = request.form.get('date')
            
            # Update optics
            if eq: optics = calculate_optics(eq)

            if loc and eq:
                # 2. Try AI
                if client:
                    full_prompt = f"Date: {date}. Loc: {loc}. Eq: {eq}. JSON Plan."
                    response = client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        config=types.GenerateContentConfig(
                            system_instruction="Output JSON Only.",
                            response_mime_type="application/json"
                        ),
                        contents=full_prompt
                    )
                    data = json.loads(response.text)
                else:
                    raise Exception("No Client")
                    
        except Exception as e:
            print(f"ERROR: {e}")
            data = MOCK_PLAN
            data['error'] = f"Demo Mode ({str(e)})"

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    return jsonify({"location": "Locating..."})

if __name__ == '__main__':
    app.run(debug=True)