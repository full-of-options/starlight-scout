from flask import Flask, render_template, request
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

# --- 🌑 ROBUST MOON MATH ---
def get_moon_data(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Reference: New Moon Nov 20, 2025
        ref_new_moon = datetime(2025, 11, 20) 
        days_passed = (dt - ref_new_moon).days
        lunation = 29.53059
        
        # Handle negative deltas (past dates) correctly using modulo
        cycle_age = days_passed % lunation
        percent = 0
        phase_name = ""
        
        if cycle_age < 1: phase_name = "New Moon"; percent = 0
        elif cycle_age < 7: phase_name = "Waxing Crescent"; percent = int((cycle_age/7)*50)
        elif cycle_age < 8: phase_name = "First Quarter"; percent = 50
        elif cycle_age < 14: phase_name = "Waxing Gibbous"; percent = 50 + int(((cycle_age-7)/7)*50)
        elif cycle_age < 16: phase_name = "Full Moon"; percent = 100
        elif cycle_age < 22: phase_name = "Waning Gibbous"; percent = 100 - int(((cycle_age-15)/7)*50)
        elif cycle_age < 23: phase_name = "Last Quarter"; percent = 50
        else: phase_name = "Waning Crescent"; percent = 50 - int(((cycle_age-22)/7)*50)
        
        return {
            "phase": f"{phase_name} ({percent}%)",
            "context": f"Moon Age: {round(cycle_age, 1)} days."
        }
    except Exception as e:
        print(f"Moon Math Error: {e}")
        return {"phase": "Unknown", "context": "Calculation Failed"}

# --- 🔭 OPTICS ENGINE ---
def calculate_optics(equipment_name):
    specs = {
        "Dwarf II": { "name": "Dwarf II", "fov_val": 3.0, "fov_desc": "3.0° x 1.6°", "icon": "🔭" },
        "Seestar S50": { "name": "Seestar S50", "fov_val": 1.3, "fov_desc": "1.3° x 0.73°", "icon": "🔭" },
        "Dwarf 3": { "name": "Dwarf 3", "fov_val": 2.9, "fov_desc": "2.9° x 1.6°", "icon": "🔭" },
        "Manual Rig": { "name": "APS-C / 250mm", "fov_val": 5.0, "fov_desc": "5.4° x 3.6°", "icon": "📷" },
        "Binoculars": { "name": "10x50 Binos", "fov_val": 6.0, "fov_desc": "6.5° Field", "icon": "👀" }
    }
    return specs.get(equipment_name, specs["Manual Rig"])

# --- 🧠 JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight. Return STRICT JSON only.

*** LOGIC RULES ***
1. MOONLIGHT: Use provided Moon Phase. If >50%, suggest Gain ~80.
2. TIME WINDOW: Only suggest targets that are high in the sky during the user's Start/End times.
3. DEVICES: Dwarf II (Max 15s). Seestar (10/20/30s). IR Mode: "Astro" or "Vis".
4. EVENTS: 3 events for the requested Calendar Month.

*** OUTPUT FORMAT ***
{
  "summary": { "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str", "type": "Str", "why": "Str",
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
    
    # Defaults for form pre-fill
    defaults = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'start': "20:00", # 8 PM
        'end': "23:00"    # 11 PM
    }
    calendar_context = datetime.now().strftime('%B %Y')

    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
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
                moon_data = get_moon_data(session_date)
                
                full_prompt = (
                    f"MISSION CONTEXT:\n"
                    f"- Session Night: {session_date}\n"
                    f"- Time Window: {start_time} to {end_time}\n"
                    f"- Moon: {moon_data['phase']}\n"
                    f"- Location: {location}\n"
                    f"- Equipment: {equipment}\n"
                    f"- Calendar Month: {calendar_context}\n\n"
                    f"TASK: Generate JSON Plan optimized for this specific time window."
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
                print(f"AI/Server Error: {e}") # Print to terminal logs
                data = {"error": f"Mission Failure: {str(e)}"}

    return render_template('index.html', data=data, optics=optics, defaults=defaults)

if __name__ == '__main__':
    app.run(debug=True)