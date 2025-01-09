import google.generativeai as genai
import json

# Configure Gemini with your API key
def configure_gemini():
    with open("SECRET.json", 'r') as file:
        data = json.load(file)

    # Access the value of 'gemini_api'
    gemini_api_value = data['info']['gemini_api']

    genai.configure(api_key=gemini_api_value)

# Generate content based on a prompt
def generate_content(prompt: str):
    configure_gemini()
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error generating content: {e}")
        return None