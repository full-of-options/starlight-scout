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
1. MOONLIGHT: If >50%, suggest Gain ~80. If >75%, avoid Galaxies.
2. DEVICES: Dwarf II (Max 15s). Seestar (10/20/30s).
3. EVENTS: Generate 3 events strictly for the requested CALENDAR MONTH/YEAR.

*** OUTPUT FORMAT ***
{
  "summary": { "moon_phase": "Str", "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str (Catalog Name)", "type": "Str", "why": "Str",
      "settings": { "exposure": "Str", "gain": "Str (Number)", "filter": "Str", "binning": "Str", "ir_mode": "Str" },
      "tips": ["Tip 1", "Tip 2"]
    }
  ],
  "events": [
    { "date": "Str (Format: Month DD)", "name": "Str", "type": "Str", "desc": "Str" }
  ]
}
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = None
    
    # Defaults
    current_date = datetime.now().strftime('%Y-%m-%d')
    calendar_context = datetime.now().strftime('%B %Y') # e.g. "December 2025"

    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        session_date = request.form.get('date')
        
        # Check if user requested a specific calendar month (Time Machine)
        req_month = request.form.get('cal_month')
        req_year = request.form.get('cal_year')
        
        if req_month and req_year:
            calendar_context = f"{req_month} {req_year}"
        elif session_date:
            # If no manual override, default calendar to the session date
            dt = datetime.strptime(session_date, "%Y-%m-%d")
            calendar_context = dt.strftime("%B %Y")

        if location and equipment and session_date:
            try:
                optics = calculate_optics(equipment)
                full_prompt = (
                    f"MISSION CONTEXT:\n"
                    f"- Session Date: {session_date} (Optimize Targets for this specific night)\n"
                    f"- Location: {location}\n"
                    f"- Equipment: {equipment}\n"
                    f"- Calendar Focus: {calendar_context} (Generate Events for this month only)\n\n"
                    f"TASK: Generate Session Plan and Calendar Events in JSON."
                )

                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.5, 
                        response_mime_type="application/json"
                    ),
                    contents=full_prompt
                )
                data = json.loads(response.text)
                # Pass the calendar context back to the UI so we know what we are looking at
                data['calendar_display'] = calendar_context
                
            except Exception as e:
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics)

if __name__ == '__main__':
    app.run(debug=True)