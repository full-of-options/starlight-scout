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

# Initialize Client safely
try:
    client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"STARTUP ERROR: {e}")
    client = None

app = Flask(__name__)

# --- 🛡️ MOCK DATA (The Safety Net) ---
MOCK_PLAN = {
  "summary": { 
      "moon_phase": "Waxing Gibbous (Simulated)", 
      "weather": "Clear Skies (Simulated)", 
      "score": 85, 
      "strategy": "DEMO MODE: API Unavailable. Showing Example Plan." 
  },
  "targets": [
    {
      "name": "M42", "type": "Emission Nebula", "why": "Brightest target for winter.",
      "settings": { "exposure": "10s", "gain": "80", "filter": "Dual-band", "binning": "2x2", "ir_mode": "Astro" },
      "tips": ["Short exposures for core.", "Stack 1hr+."]
    },
    {
      "name": "M45", "type": "Open Cluster", "why": "The Pleiades. Stunning blue stars.",
      "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" },
      "tips": ["Watch for star halos.", "Needs dark skies."]
    },
    {
      "name": "M31", "type": "Galaxy", "why": "Andromeda Galaxy.",
      "settings": { "exposure": "15s", "gain": "100", "filter": "None", "binning": "2x2", "ir_mode": "Astro" },
      "tips": ["Framing is key.", "Bright core."]
    }
  ],
  "events": [ { "date": "Dec 13", "name": "Geminids", "type": "Meteor Shower", "desc": "Peak activity." } ]
}

# --- 🧹 TEXT CLEANER ---
def clean_json_text(text):
    text = text.strip()
    # Find the first { and the last }
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != -1:
        return text[start:end]
    return text

# --- 🔭 OPTICS ENGINE ---
def calculate_optics(equipment_name):
    if not equipment_name: return { "name": "Unknown", "fov_val": 5.0, "icon": "📷" }
    name = str(equipment_name).lower()
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    
    if "dwarf" in name: specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name: specs = { "name": "Redcat 51", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name: specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    
    return specs

# --- 🧠 LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = "You are a JSON DATA ENGINE. Output strictly JSON. Rules: Moon>50%=Gain 80. Dwarf=15s Max."

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = None
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        print("--- STARTING MISSION ---")
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        
        # 1. ALWAYS CALCULATE OPTICS FIRST (Prevents HTML Crash)
        optics = calculate_optics(equipment)
        print(f"Optics Calculated: {optics['name']}")

        if location and equipment:
            try:
                full_prompt = f"Date: {session_date}. Location: {location}. Equipment: {equipment}. Generate JSON Plan."
                print("Sending request to Google AI...")

                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                print("AI Response Received.")
                
                clean_text = clean_json_text(response.text)
                data = json.loads(clean_text)
                print("JSON Parsed Successfully.")
                
            except Exception as e:
                print(f"❌ CRITICAL ERROR: {e}")
                # FALLBACK TO MOCK DATA
                data = MOCK_PLAN
                data['error'] = f"Demo Mode (Error: {str(e)})"

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

# --- 🌍 GEOCODER ---
@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        lat, lon = data.get('lat'), data.get('lon')
        # Simple Fallback Model
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Convert {lat},{lon} to 'City, State' only. No chat."
        )
        return jsonify({"location": response.text.strip()})
    except Exception:
        return jsonify({"location": "Location Found"})

if __name__ == '__main__':
    app.run(debug=True)