from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

# Connect to Google
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- AVAILABLE MODELS FOR YOU ---")
try:
    # Ask for the list
    for m in client.models.list():
        # Only show models that support "generateContent" (the chat feature)
        if "generateContent" in m.supported_actions:
            print(f"Name: {m.name}")
            print(f"   --> Use this ID in your code: {m.name.split('/')[-1]}")
            print("-" * 30)
except Exception as e:
    print(f"Error: {e}")