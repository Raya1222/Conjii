import google.generativeai as genai
import os

# Configure Gemini with your API key
def configure_gemini():
    #api_key = os.getenv("GENAI_API_KEY")  # Ensure your API key is set in your environment variables
    api_key = "AIzaSyCq2ayJ_paj3pxngOTTFLVWViL_frkzJ2Q"
    genai.configure(api_key=api_key)

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