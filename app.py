from flask import Flask, render_template, request
import os
import json
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

app = Flask(__name__)

# --- 🌑 PRECISE MOON MATH (2025 Calibrated) ---
def get_moon_data(date_str):
    """Calculates phase and provides context anchors for the AI."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # ANCHOR: Known New Moon on Nov 20, 2025 at 01:47 UTC
    # Synodic Month (New Moon to New Moon) = 29.53059 days
    ref_new_moon = datetime(2025, 11, 20)
    
    # Days since reference
    days_passed = (dt - ref_new_moon).days
    lunation = 29.53059
    
    # Current position in cycle (0.0 to 29.53)
    cycle_age = days_passed % lunation
    percent = 0.0
    phase_name = ""
    
    # Determine Phase
    if cycle_age < 1: phase_name = "New Moon"; percent = 0
    elif cycle_age < 7: phase_name = "Waxing Crescent"; percent = int((cycle_age/14.7)*100)
    elif cycle_age < 8: phase_name = "First Quarter"; percent = 50
    elif cycle_age < 14: phase_name = "Waxing Gibbous"; percent = int((cycle_age/14.7)*100)
    elif cycle_age < 16: phase_name = "Full Moon"; percent = 100
    elif cycle_age < 22: phase_name = "Waning Gibbous"; percent = int(((lunation-cycle_age)/14.7)*100)
    elif cycle_age < 23: phase_name = "Last Quarter"; percent = 50
    else: phase_name = "Waning Crescent"; percent = int(((lunation-cycle_age)/14.7)*100)
    
    # Calculate the *actual* dates of Full/New moon for this month to correct the AI
    # This prevents it from saying "Full Moon is Dec 15" when it was Dec 4
    return {
        "phase": f"{phase_name} ({percent}%)",
        "age": round(cycle_age, 1),
        "context": f"Current Moon Age is {round(cycle_age, 1)} days old. (0=New, 15=Full). Use this to sanity check dates."
    }

# --- 🔭 THE OPTICS ENGINE ---
def calculate_optics(equipment_name):
    specs = {
        "Dwarf II": { "name": "Dwarf II", "fov_val": 3.0, "fov_desc": "3.0° x 1.6°", "icon": "🔭" },
        "Seestar S50": { "name": "Seestar S50", "fov_val": 1.3, "fov_desc": "1.3° x 0.73°", "icon": "🔭" },
        "Dwarf 3": { "name": "Dwarf 3", "fov_val": 2.9, "fov_desc": "2.9° x 1.6°", "icon": "🔭" },
        "Manual Rig": { "name": "APS-C / 250mm", "fov_val": 5.0, "fov_desc": "5.4° x 3.6°", "icon": "📷" },
        "Binoculars": { "name": "10x50 Binos", "fov_val": 6.5, "fov_desc": "6.5° Field", "icon": "👀" }
    }
    return specs.get(equipment_name, specs["Manual Rig"])

# --- 🧠 THE JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.

*** LOGIC RULES ***
1. MOONLIGHT: Use the provided Moon Age/Phase. 
   - If Age is 13-17 (Full): Avoid Galaxies. Target Emission Nebulae. Gain: 80.
   - If Age is 0-4 (New): Galaxies allowed. Gain: 100-120.
2. DEVICES: 
   - Dwarf II: Max Exp 15s. IR Mode: "Astro" or "Vis". Gain: Number (0-240).
   - Seestar: Exp 10s/20s/30s. Gain: High.
3. CALENDAR: Use the Moon Age to sanity check events. 
   - If Moon Age is 18 (Waning Gibbous), the Full Moon was ~3 days ago. Do not list it as a future event.

*** OUTPUT FORMAT ***
{
  "summary": { "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str (Catalog Name)", "type": "Str", "why": "Str",
      "settings": { "exposure": "Str", "gain": "Str (Number)", "filter": "Str", "binning": "Str", "ir_mode": "Str" },
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
    current_date = datetime.now().strftime('%Y-%m-%d')
    calendar_context = datetime.now().strftime('%B %Y')

    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        
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
                moon_data = get_moon_data(session_date)
                
                full_prompt = (
                    f"MISSION CONTEXT:\n"
                    f"- Date: {session_date}\n"
                    f"- Moon Phase: {moon_data['phase']} ({moon_data['context']})\n"
                    f"- Location: {location}\n"
                    f"- Equipment: {equipment}\n"
                    f"- Calendar Focus: {calendar_context}\n\n"
                    f"TASK: Generate JSON Plan. Ensure 'Gain' is a number and IR Mode is valid."
                )

                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.1, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                data = json.loads(response.text)
                data['calendar_display'] = calendar_context
                data['summary']['moon_phase'] = moon_data['phase']
                
            except Exception as e:
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics)

if __name__ == '__main__':
    app.run(debug=True)