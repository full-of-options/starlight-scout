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
    """Returns the sensor specs and calculated FOV description."""
    # Based on actual sensor specs from your blueprints
    specs = {
        "Dwarf II": {
            "name": "Dwarf II (Telephoto)", 
            "fov_desc": "3.2° x 1.8° (Sony IMX415)",
            "icon": "🔭" 
        },
        "Seestar S50": {
            "name": "Seestar S50", 
            "fov_desc": "1.3° x 0.73° (Sony IMX462)",
            "icon": "🔭"
        },
        "Dwarf 3": {
            "name": "Dwarf 3 (Telephoto)", 
            "fov_desc": "2.9° x 1.6°",
            "icon": "🔭"
        },
        "Manual Rig": {
            "name": "Standard APS-C / 250mm", 
            "fov_desc": "5.4° x 3.6°",
            "icon": "📷"
        },
        "Binoculars": {
            "name": "Standard 10x50", 
            "fov_desc": "6.5° Field",
            "icon": "👀"
        }
    }
    # Default to Manual Rig if unknown
    return specs.get(equipment_name, specs["Manual Rig"])

# --- 🧠 THE JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight, an API that outputs strict JSON data.
*** LOGIC RULES ***
1. MOONLIGHT: If >50%, reduce Gain. If >75%, avoid Galaxies; prioritize Emission Nebulae.
2. DEVICES: Dwarf II (Max 15s, Bin 2x2), Seestar (10/20/30s).
*** OUTPUT FORMAT ***
{
  "summary": { "moon_phase": "Str", "weather": "Str", "score": "Int", "strategy": "Str" },
  "targets": [
    {
      "name": "Str", "type": "Str", "why": "Str",
      "settings": { "exposure": "Str", "gain": "Str", "filter": "Str", "binning": "Str", "ir_mode": "Str" },
      "tips": ["Tip 1", "Tip 2"]
    }
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
                # 1. Run the Optics Engine
                optics = calculate_optics(equipment)

                # 2. Run the AI Engine
                full_prompt = (
                    f"Date: {date}\nLocation: {location}\nEquipment: {equipment}\n"
                    f"Generate 3 best targets in JSON format."
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
                print(f"Error: {e}")
                data = {"error": str(e)}

    return render_template('index.html', data=data, optics=optics)

if __name__ == '__main__':
    app.run(debug=True)