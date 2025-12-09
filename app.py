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
        if not data: return jsonify({"location": "Manual Entry Required"})
        lat, lon = data.get('lat'), data.get('lon')
        if not lat or not lon: return jsonify({"location": "Invalid Coordinates"})

        try:
            # FIX: Using 'gemini-2.5-flash-lite' (On your list!)
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=f"Convert {lat},{lon} to 'City, State' only."
            )
            clean_loc = response.text.strip().replace('\n', '').replace('"', '')
            return jsonify({"location": clean_loc})
        except Exception as e:
            print(f"Geo Error: {e}")
            return jsonify({"location": f"{lat:.2f}, {lon:.2f}"})
    except Exception as e:
        return jsonify({"location": "Location Error"})

# --- 🔭 OPTICS ENGINE ---
def calculate_optics(equipment_name):
    name = str(equipment_name).lower()
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    
    if "dwarf" in name: specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name: specs = { "name": "Redcat 51", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name: specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    elif "rokinon" in name: specs = { "name": "135mm Lens", "fov_val": 10.0, "icon": "📷" }
    elif "vespera" in name: specs = { "name": "Vespera", "fov_val": 1.6, "icon": "🔭" }
    
    return specs

# --- 🧠 JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.
RULES: 
1. Moon > 50% = Gain 80. 
2. Dwarf II Max Exp 15s.
OUTPUT: { "summary": {...}, "targets": [...], "events": [...] }
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
        
        if location and equipment:
            try:
                optics = calculate_optics(equipment)
                full_prompt = f"Date: {session_date}. Location: {location}. Equipment: {equipment}. Generate JSON Plan."

                # FIX: Using 'gemini-2.5-flash-lite' (On your list!)
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
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