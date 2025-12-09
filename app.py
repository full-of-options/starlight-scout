from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = Flask(__name__)

# --- 🌍 ROBUST REVERSE GEOCODER ---
@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"location": "Manual Entry Required"})
            
        lat = data.get('lat')
        lon = data.get('lon')
        
        if not lat or not lon:
            return jsonify({"location": "Invalid Coordinates"})

        try:
            # FIX: Using a model explicitly listed in your menu
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite-001",
                contents=f"Convert these coordinates to a City, State string: {lat}, {lon}. Return ONLY the text 'City, State' (e.g. Poway, CA). Do not include coordinates."
            )
            clean_loc = response.text.strip().replace('\n', '').replace('"', '')
            return jsonify({"location": clean_loc})
            
        except Exception as api_error:
            print(f"Gemini Geo Error: {api_error}")
            return jsonify({"location": f"{lat:.2f}, {lon:.2f}"})

    except Exception as e:
        print(f"Server Geo Error: {e}")
        return jsonify({"location": "Location Error"})

# --- 🔭 OPTICS ENGINE ---
def calculate_optics(equipment_name):
    name = str(equipment_name).lower()
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    
    if "dwarf" in name:
        specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name:
        specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name:
        specs = { "name": "Redcat 51", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name:
        specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    elif "rokinon" in name:
        specs = { "name": "135mm Lens", "fov_val": 10.0, "icon": "📷" }
    elif "vespera" in name or "stellina" in name:
        specs = { "name": "Vaonis Smart Scope", "fov_val": 1.6, "icon": "🔭" }
        
    return specs

# --- 🧠 JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.

*** LOGIC RULES ***
1. MOONLIGHT: Use provided Moon Phase.
2. DEVICES: 
   - Dwarf II: Max Exp 15s. IR Mode MUST be "Astro" or "Vis".
   - Seestar: Exp 10s/20s/30s.
3. IMAGES: Use standard catalog names (e.g. "M42", "M31") for best image lookup.

*** OUTPUT FORMAT ***
{
  "summary": { "moon_phase": "Str", "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str (e.g. M42)", "type": "Str", "why": "Str",
      "settings": { "exposure": "Str", "gain": "Str", "filter": "Str", "binning": "Str", "ir_mode": "Str" },
      "tips": ["Tip 1", "Tip 2"]
    }
  ],
  "events": [ { "date": "Str", "name": "Str", "type": "Str", "desc": "Str" } ]
}
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = None
    defaults = { 'date': datetime.now().strftime('%Y-%m-%d'), 'start': "20:00", 'end': "23:00" }

    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        
        if location and equipment and session_date:
            try:
                optics = calculate_optics(equipment)
                full_prompt = (
                    f"MISSION CONTEXT:\n"
                    f"- Date: {session_date}\n"
                    f"- Location: {location}\n"
                    f"- Equipment: {equipment}\n"
                    f"TASK: Generate JSON Plan."
                )

                # FIX: Using specific model from your list
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite-001", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.3, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                data = json.loads(response.text)
                
            except Exception as e:
                data = {"error": f"Mission Error: {str(e)}"}

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

if __name__ == '__main__':
    app.run(debug=True)