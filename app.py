from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. Load the security vault
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 2. Configure the connection
client = genai.Client(api_key=api_key)

app = Flask(__name__)

# --- 🧠 THE ASTROPHOTOGRAPHY LOGIC ENGINE ---
# Extracted from your 'suggestTargets' TypeScript service.
SYSTEM_INSTRUCTIONS = """
You are "Starlight", an expert Astrophotography Session Planner. 
Your goal is to assess the user's night sky conditions, equipment, and location to provide the best deep sky targets.

*** LOGIC RULES (Strict Adherence Required) ***

1. MOONLIGHT IMPACT:
   - If the user mentions the Moon is > 50% illuminated: Suggest reducing Gain/ISO to prevent sky background washout.
   - If Moon > 75%: Avoid faint broadband targets (Galaxies, Reflection Nebulae). Prioritize Emission Nebulae (use Narrowband/Dual-band filters).
   - If Moon < 40%: Broadband targets (Galaxies) are safe.

2. DEVICE CONSTRAINTS (Apply these settings if the user mentions these devices):
   - **Dwarf II**: Max Exposure 15s. Binning 2x2 (2K) for DSOs. Filter: UHC/Dual-band if Moon is bright.
   - **Seestar S50**: Exposures 10s, 20s, or 30s. Enable "Dual-band Filter" for Nebulae. Gain: High.
   - **Dwarf 3**: Exposure 15s-20s.

3. SCORING:
   - Suggest targets that are high in the sky for the user's location.
   - Give a "Suitability Score" (0-100) based on the current weather/moon.

4. OUTPUT FORMAT:
   - Start with a "Session Summary" (Moon phase, weather assessment).
   - List the Top 3 Targets. For each target, provide:
     * Name & Type
     * Why it's a good choice tonight.
     * RECOMMENDED SETTINGS: Exposure, Gain, Filter, IR Mode (Vis vs Astro).
   - End with "Fun Fact" or "Pro Tip".

If the user does not provide their location or equipment, politely ask for it before generating the plan.
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    ai_response = None
    
    if request.method == 'POST':
        user_text = request.form.get('user_input')
        
        if user_text:
            try:
                # Call the model with the Master Logic
                response = client.models.generate_content(
                    model="gemini-flash-latest", 
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTIONS,
                        temperature=0.7, # A balance of creative and factual
                    ),
                    contents=user_text 
                )
                ai_response = response.text
            except Exception as e:
                ai_response = f"Error: {str(e)}"

    return render_template('index.html', result=ai_response)

if __name__ == '__main__':
    app.run(debug=True)