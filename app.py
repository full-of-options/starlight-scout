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
2. DEVICES: 
   - Dwarf II: Max Exp 15s. IR Mode is "Astro" (Pass) or "Vis" (Cut).
   - Seestar: Exp 10s/20s/30s.

*** OUTPUT FORMAT ***
{
  "summary": { "moon_phase": "Str", "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "String (Standard Catalog Name, e.g. M42)",
      "type": "String", 
      "why": "String",
      "settings": { 
        "exposure": "String (e.g. 15s)", 
        "gain": "String (NUMBER ONLY, e.g. 80)", 
        "filter": "String (Physical filter ONLY: UHC, Dual-band, or None. Do NOT put IR Cut here.)", 
        "binning": "String (e.g. 2x2)", 
        "ir_mode": "String (Astro or Vis)" 
      },
      "tips": ["Tip 1", "Tip 2"]
    }
  ],
  "events": [
    { "date": "Str", "name": "Str", "type": "Str", "desc": "Str" }
  ]
}
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    optics = None
    
    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        date = request.form.get('date')
        
        if location and equipment and date:
            try:
                optics = calculate_optics(equipment)
                full_prompt = (
                    f"Date: {date}\nLocation: {location}\nEquipment: {equipment}\n"
                    f"Generate Plan + 3 Monthly Events."
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
            except Exception as e:
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics)

if __name__ == '__main__':
    app.run(debug=True)