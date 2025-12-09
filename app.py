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

# --- 🧠 THE JSON LOGIC ENGINE ---
SYSTEM_INSTRUCTIONS = """
You are Starlight, an API that outputs strict JSON data for astrophotography planning.
You DO NOT speak conversational text. You ONLY return a JSON object.

*** LOGIC RULES ***
1. MOONLIGHT: 
   - If Moon > 50%: Suggest reducing Gain.
   - If Moon > 75%: Avoid Galaxies. Prioritize Emission Nebulae (Dual-band/UHC).
   - If Moon < 40%: Galaxies are safe.
2. DEVICES:
   - Dwarf II: Max Exp 15s. Binning 2x2 (2K). IR Mode: Astro.
   - Seestar S50: Exp 10/20/30s. Gain: High.
   - Manual Rig: Suggest standard NINA/ASIAIR settings.

*** OUTPUT FORMAT ***
Return a single JSON object with this exact structure:
{
  "summary": {
    "moon_phase": "String (e.g. Waxing Gibbous 75%)",
    "weather": "String (Short assessment)",
    "score": "Integer (0-100)",
    "strategy": "String (Short advice for the night)"
  },
  "targets": [
    {
      "name": "String (e.g. M42 Orion Nebula)",
      "type": "String (e.g. Emission Nebula)",
      "constellation": "String",
      "difficulty": "String (Easy/Medium/Hard)",
      "why": "String (Why is it good tonight?)",
      "settings": {
        "exposure": "String (e.g. 15s)",
        "gain": "String (e.g. 100)",
        "filter": "String (e.g. Dual-band)",
        "binning": "String (e.g. 2x2)",
        "ir_mode": "String (e.g. Astro)"
      },
      "tips": [ "String tip 1", "String tip 2" ]
    }
  ]
}
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    data = None
    
    if request.method == 'POST':
        location = request.form.get('location')
        equipment = request.form.get('equipment')
        date = request.form.get('date')
        
        if location and equipment and date:
            try:
                full_prompt = (
                    f"Date: {date}\nLocation: {location}\nEquipment: {equipment}\n"
                    f"Generate 3 best targets in JSON format."
                )

                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.5, # Lower temp for consistent JSON
                        response_mime_type="application/json" # <--- THE MAGIC KEY
                    ),
                    contents=full_prompt
                )
                
                # Parse the text response into a real Python Dictionary
                data = json.loads(response.text)
                
            except Exception as e:
                print(f"Error: {e}")
                data = {"error": str(e)}

    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)