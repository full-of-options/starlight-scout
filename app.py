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

# --- 🌍 REVERSE GEOCODER (Using Gemini) ---
@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    data = request.json
    lat = data.get('lat')
    lon = data.get('lon')
    try:
        # Ask Gemini to identify the city
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=f"Identify the City and State/Country for coordinates: {lat}, {lon}. Return ONLY the string 'City, State' (e.g. Poway, CA)."
        )
        return jsonify({"location": response.text.strip()})
    except Exception as e:
        return jsonify({"location": f"{lat}, {lon}"}) # Fallback to coords

# --- 🔭 EXPANDED OPTICS ENGINE ---
def calculate_optics(equipment_name):
    # Default Specs
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    
    # Keyword Matching for common gear
    name = equipment_name.lower()
    if "dwarf ii" in name or "dwarf 2" in name:
        specs = { "name": "Dwarf II", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name:
        specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name:
        specs = { "name": "Redcat 51 (APS-C)", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name or "sct" in name:
        specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    elif "rokinon" in name:
        specs = { "name": "135mm Lens", "fov_val": 10.0, "icon": "📷" }
        
    return specs

# --- 🧠 JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.

*** LOGIC RULES ***
1. MOONLIGHT: Use provided Moon Phase. If >50%, suggest Gain ~80.
2. DEVICES: Dwarf II (Max 15s). Seestar (10/20/30s).
3. WEATHER: Generate a realistic "Forecast" based on the season/location (Simulated).

*** OUTPUT FORMAT ***
{
  "summary": { "moon_phase": "Str", "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str", "type": "Str", "why": "Str",
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
    
    # Defaults
    defaults = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'start': "20:00", 
        'end': "23:00"
    }

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

                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.3, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                data = json.loads(response.text)
                
            except Exception as e:
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

if __name__ == '__main__':
    app.run(debug=True)