from flask import Flask, render_template, request, jsonify
import os
import json
import re
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize Client safely - prevents startup crash if key is bad
try:
    client = genai.Client(api_key=api_key)
except:
    client = None

app = Flask(__name__)

# --- 🛡️ MOCK DATA (The Safety Net) ---
MOCK_PLAN = {
  "summary": { 
      "moon_phase": "Waxing Gibbous", 
      "weather": "Clear (Simulated)", 
      "score": 85, 
      "strategy": "DEMO MODE: Showing example data due to connection issue." 
  },
  "targets": [
    { 
      "name": "M42", "type": "Nebula", "why": "Brightest winter target.", 
      "settings": { "exposure": "10s", "gain": "80", "filter": "Dual", "binning": "2x2", "ir_mode": "Astro" }, 
      "tips": ["Short exposures for core."] 
    },
    { 
      "name": "M45", "type": "Cluster", "why": "Pleiades Cluster.", 
      "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" }, 
      "tips": ["Watch for star halos."] 
    }
  ],
  "events": []
}

def clean_json_text(text):
    """Extracts JSON from markdown code blocks."""
    text = text.strip()
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != -1: return text[start:end]
    return text

def calculate_optics(equipment_name):
    # Default fallback - ensures optics is NEVER None
    default_specs = { "name": "Unknown Device", "fov_val": 5.0, "icon": "📷" }
    
    if not equipment_name: return default_specs
    
    name = str(equipment_name).lower()
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    
    if "dwarf" in name: specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name: specs = { "name": "Redcat 51", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name: specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    
    return specs

SYSTEM_INSTRUCTIONS = "You are a JSON engine. Output strict JSON only."

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    # 1. Initialize optics with a safe default IMMEDIATELY
    # This prevents the 'NoneType' crash in the HTML template
    optics = { "name": "Setup", "fov_val": 5.0, "icon": "📷" }
    
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        try:
            location = request.form.get('location')
            equipment = request.form.get('equipment')
            session_date = request.form.get('date')
            
            # Update optics based on input
            if equipment:
                optics = calculate_optics(equipment)

            if location and equipment:
                full_prompt = f"Date: {session_date}. Location: {location}. Equipment: {equipment}. Generate JSON Plan."
                
                if not client: raise Exception("API Client not initialized")

                # Using verified Lite model
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                
                clean_text = clean_json_text(response.text)
                data = json.loads(clean_text)
                
        except Exception as e:
            print(f"CRASH CAUGHT: {e}")
            # Fallback to Mock Data so the user sees SOMETHING
            data = MOCK_PLAN
            data['error'] = f"System Message: {str(e)} (Showing Demo Data)"

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

# Simplified Geocoder to prevent crashes
@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        lat, lon = data.get('lat'), data.get('lon')
        if not client: return jsonify({"location": f"{lat:.3f}, {lon:.3f}"})
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=f"Convert {lat},{lon} to 'City, State' only. No text."
        )
        return jsonify({"location": response.text.strip()})
    except:
        return jsonify({"location": "Location Found"})

if __name__ == '__main__':
    app.run(debug=True)