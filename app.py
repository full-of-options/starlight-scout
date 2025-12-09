from flask import Flask, render_template, request, jsonify
import os
import json
import re # regex for cleaning text
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = Flask(__name__)

# --- 🛡️ MOCK DATA (Safety Net) ---
MOCK_PLAN = {
  "summary": { "moon_phase": "Waxing Gibbous (85%)", "weather": "Simulated Clear Skies", "score": 85, "strategy": "DEMO MODE: API Quota Hit. Showing Example Plan." },
  "targets": [
    { "name": "M42", "type": "Emission Nebula", "why": "Brightest winter target. Excellent for testing.", "settings": { "exposure": "10s", "gain": "80", "filter": "Dual-band", "binning": "2x2", "ir_mode": "Astro" }, "tips": ["Short exposures for core.", "Stack 1hr+."] },
    { "name": "M45", "type": "Open Cluster", "why": "The Pleiades. Stunning blue reflection nebula.", "settings": { "exposure": "10s", "gain": "80", "filter": "None", "binning": "2x2", "ir_mode": "Vis" }, "tips": ["Watch for star halos.", "Needs dark skies."] },
    { "name": "NGC 2237", "type": "Emission Nebula", "why": "Rosette Nebula. Large and colorful.", "settings": { "exposure": "15s", "gain": "100", "filter": "Dual-band", "binning": "2x2", "ir_mode": "Astro" }, "tips": ["Mosaic candidate.", "Framing is key."] }
  ],
  "events": [ { "date": "Dec 13", "name": "Geminids Peak", "type": "Meteor Shower", "desc": "120 meteors/hour." } ]
}

# --- 🧹 TEXT CLEANERS ---
def clean_json_text(text):
    """Removes markdown code blocks to extract pure JSON."""
    text = text.strip()
    # Remove ```json ... ``` wrappers
    if text.startswith("```"):
        text = re.sub(r"^```json\s*", "", text) # Remove start
        text = re.sub(r"\s*```$", "", text)     # Remove end
    return text

def clean_geo_text(text):
    """Extracts just the City, State from a chatty response."""
    # Look for bold text like **San Diego, California**
    match = re.search(r'\*\*(.*?)\*\*', text)
    if match:
        return match.group(1)
    # If no bold, try to split by newline and take the shortest line
    lines = text.split('\n')
    for line in lines:
        if ',' in line and len(line) < 50:
            return line.strip()
    return text[:50] # Fallback: return first 50 chars

# --- 🔭 OPTICS ENGINE ---
def calculate_optics(equipment_name):
    name = str(equipment_name).lower()
    specs = { "name": equipment_name, "fov_val": 5.0, "icon": "📷" }
    if "dwarf" in name: specs = { "name": "Dwarf II/3", "fov_val": 3.0, "icon": "🔭" }
    elif "seestar" in name: specs = { "name": "Seestar S50", "fov_val": 1.3, "icon": "🔭" }
    elif "redcat" in name: specs = { "name": "Redcat 51", "fov_val": 4.5, "icon": "📷" }
    elif "c8" in name: specs = { "name": "Celestron C8", "fov_val": 0.6, "icon": "🔭" }
    elif "rokinon" in name: specs = { "name": "135mm Lens", "fov_val": 10.0, "icon": "📷" }
    return specs

# --- 🧠 JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are a JSON DATA ENGINE. You do NOT speak English. You ONLY output JSON.
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

                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1, # Extremely strict
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                
                # CLEAN AND PARSE
                clean_text = clean_json_text(response.text)
                data = json.loads(clean_text)
                
            except Exception as e:
                print(f"API Failed: {e}")
                data = MOCK_PLAN
                data['error'] = f"System Offline ({str(e)}). Using Cached Data."

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

# --- 🌍 ROBUST REVERSE GEOCODER ---
@app.route('/reverse-geocode', methods=['POST'])
def reverse_geocode():
    try:
        data = request.get_json()
        lat, lon = data.get('lat'), data.get('lon')
        
        try:
            # We use a very aggressive prompt to stop the chatting
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=f"You are a database. Convert {lat},{lon} to 'City, State'. Output ONLY the city name. No chat. No warnings."
            )
            # Use the cleaner to strip formatting
            clean_loc = clean_geo_text(response.text)
            return jsonify({"location": clean_loc})
            
        except Exception as e:
            return jsonify({"location": f"{lat:.3f}, {lon:.3f}"}) # Fallback to coords
            
    except Exception as e:
        return jsonify({"location": "Locating..."})

if __name__ == '__main__':
    app.run(debug=True)