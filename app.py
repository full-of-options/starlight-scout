from flask import Flask, render_template, request
import os
import json
import math
from datetime import datetime
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = Flask(__name__)

# --- 🌑 MOON PHASE CALCULATOR (Math, not AI) ---
def get_moon_phase(date_str):
    """Calculates approximate moon phase percentage and name."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Known new moon reference: Jan 6, 2000
    ref_date = datetime(2000, 1, 6)
    diff = (dt - ref_date).days
    # Lunar cycle is approx 29.53 days
    cycle = 29.53
    position = (diff % cycle) / cycle
    
    percent = 0
    phase_name = ""
    
    if position < 0.03: phase_name = "New Moon"; percent = 0
    elif position < 0.25: phase_name = "Waxing Crescent"; percent = int(position * 200)
    elif position < 0.28: phase_name = "First Quarter"; percent = 50
    elif position < 0.48: phase_name = "Waxing Gibbous"; percent = int(position * 200)
    elif position < 0.53: phase_name = "Full Moon"; percent = 100
    elif position < 0.75: phase_name = "Waning Gibbous"; percent = int((1-position) * 200)
    elif position < 0.78: phase_name = "Last Quarter"; percent = 50
    else: phase_name = "Waning Crescent"; percent = int((1-position) * 200)
    
    return f"{phase_name} ({percent}%)"

# --- 🔭 THE OPTICS ENGINE ---
def calculate_optics(equipment_name):
    specs = {
        "Dwarf II": { "name": "Dwarf II", "fov_val": 3.0, "fov_desc": "3.0° x 1.6°", "icon": "🔭" },
        "Seestar S50": { "name": "Seestar S50", "fov_val": 1.3, "fov_desc": "1.3° x 0.73°", "icon": "🔭" },
        "Dwarf 3": { "name": "Dwarf 3", "fov_val": 2.9, "fov_desc": "2.9° x 1.6°", "icon": "🔭" },
        "Manual Rig": { "name": "APS-C / 250mm", "fov_val": 5.0, "fov_desc": "5.4° x 3.6°", "icon": "📷" },
        "Binoculars": { "name": "10x50 Binos", "fov_val": 6.0, "fov_desc": "6.5° Field", "icon": "👀" }
    }
    return specs.get(equipment_name, specs["Manual Rig"])

# --- 🧠 THE JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.

*** LOGIC RULES ***
1. MOONLIGHT: The system will provide the exact moon phase. Use this to determine strategy.
2. DEVICES: 
   - Dwarf II: Max Exp 15s. 
   - IR MODE: MUST BE "Astro" OR "Vis". NEVER "Off" or "None".
   - GAIN: MUST BE a Number (e.g. 80). Do not write "Low" or "High".
   - FILTER: Physical filters only (UHC, Dual-band, None).
3. EVENTS: Generate 3 events strictly for the requested CALENDAR MONTH.

*** OUTPUT FORMAT ***
{
  "summary": { "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str (Catalog Name)", "type": "Str", "why": "Str",
      "settings": { "exposure": "Str", "gain": "Str", "filter": "Str", "binning": "Str", "ir_mode": "Str" },
      "tips": ["Tip 1", "Tip 2"]
    }
  ],
  "events": [ { "date": "Str (Month DD)", "name": "Str", "type": "Str", "desc": "Str" } ]
}
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = None
    
    # Defaults
    current_date = datetime.now().strftime('%Y-%m-%d')
    calendar_context = datetime.now().strftime('%B %Y')

    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        
        # Calendar Logic
        req_month = request.form.get('cal_month')
        req_year = request.form.get('cal_year')
        if req_month and req_year:
            calendar_context = f"{req_month} {req_year}"
        elif session_date:
            dt = datetime.strptime(session_date, "%Y-%m-%d")
            calendar_context = dt.strftime("%B %Y")

        if location and equipment and session_date:
            try:
                optics = calculate_optics(equipment)
                # CALCULATE MOON PHASE (Deterministic)
                real_moon = get_moon_phase(session_date)
                
                full_prompt = (
                    f"MISSION CONTEXT:\n"
                    f"- Session Date: {session_date}\n"
                    f"- Exact Moon Phase: {real_moon} (USE THIS TRUTH)\n"
                    f"- Location: {location}\n"
                    f"- Equipment: {equipment}\n"
                    f"- Calendar Focus: {calendar_context}\n\n"
                    f"TASK: Generate JSON Plan."
                )

                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1, # <--- VERY STRICT
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                data = json.loads(response.text)
                data['calendar_display'] = calendar_context
                # Inject the real moon phase back into the summary so it's always right
                data['summary']['moon_phase'] = real_moon
                
            except Exception as e:
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics)

if __name__ == '__main__':
    app.run(debug=True)