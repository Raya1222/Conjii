import os
import io
import wave
import json
import base64
from collections import OrderedDict
import requests
import google.generativeai as genai
from pypdf import PdfReader  

def load_api_key():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        secret_path = os.path.join(base_dir, 'SECRET.json')
        
        with open(secret_path, 'r') as file:
            data = json.load(file)
            # THIS LINE CHANGED: No more 'info' block!
            return data.get('GEMINI_API_KEY')
            
    except Exception as e:
        print(f"ERROR reading SECRET.json: {e}")
        return None

api_key = load_api_key()

# Change the model in one place
MODEL_NAME = 'gemini-3.6-flash'
TTS_MODELS_INTERACTIONS = ['gemini-3.8-flash-tts', 'gemini-3.8-flash-lite-tts']
TTS_MODELS_GENERATE = ['gemini-2.5-flash-preview-tts', 'gemini-3.1-flash-tts-preview']
DEFAULT_TTS_VOICE = 'Aoede'

# Curated human-like voices exposed in the UI
TTS_VOICES = [
    ("Aoede", "Aoede — Warm & natural"),
    ("Kore", "Kore — Clear & poised"),
    ("Charon", "Charon — Calm & deep"),
    ("Leda", "Leda — Soft & youthful"),
    ("Puck", "Puck — Lively & expressive"),
]

if api_key:
    genai.configure(api_key=api_key)
    print("SUCCESS: Loaded API key securely from SECRET.json")
else:
    print("WARNING: Could not load Gemini API key from SECRET.json")

# NEW: Helper function to extract text from PDFs
def extract_text_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""

# UPDATED: Now accepts 'syllabus_context'
def generate_content(prompt, syllabus_context=""):
    if not api_key:
        return "Error: No API key configured in SECRET.json."
        
    # Prepend the syllabus/worksheet material if the user provided it
    full_prompt = prompt
    if syllabus_context.strip():
        full_prompt = (
            f"--- CLASS TOPICS & WORKSHEET CONTEXT ---\n"
            f"{syllabus_context.strip()}\n"
            f"----------------------------------------\n\n"
            f"Task Instructions:\n{prompt}\n\n"
            f"Please strictly tailor the exercises, vocabulary, and grammar "
            f"to match the provided curriculum context above."
        )

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(full_prompt)
        return response.text if response.text else "Error: Empty response returned."
    except Exception as e:
        return f"Error: {e}"


def _build_prompt(prompt, syllabus_context=""):
    if not syllabus_context.strip():
        return prompt
    return (
        f"--- CLASS TOPICS & WORKSHEET CONTEXT ---\n"
        f"{syllabus_context.strip()}\n"
        f"----------------------------------------\n\n"
        f"Task Instructions:\n{prompt}\n\n"
        f"Please strictly tailor the content, vocabulary, and grammar "
        f"to match the provided curriculum context above."
    )


# NEW: Ask Gemini for structured JSON (used by Practice, Roleplay, and Dictée).
# Supports an optional image_part={"mime_type": ..., "data": bytes} for handwritten uploads.
def generate_json(prompt, syllabus_context="", temperature=0.8, image_part=None):
    if not api_key:
        raise RuntimeError("No API key configured in SECRET.json.")

    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": temperature,
        },
    )
    built = _build_prompt(prompt, syllabus_context)
    contents = [built, image_part] if image_part else built
    response = model.generate_content(contents)
    text = (response.text or "").strip()

    # Be forgiving if the model wraps the JSON in ```json fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return json.loads(text)


# ---------------------------------------------------------------------------
# HUMAN-LIKE AI SPEECH (Gemini TTS)
# ---------------------------------------------------------------------------

_TTS_CACHE = OrderedDict()
_TTS_CACHE_MAX = 120


def _ensure_wav(audio_bytes, sample_rate=24000):
    """Ensure returned audio bytes have a standard RIFF WAV header."""
    if audio_bytes[:4] == b"RIFF":
        return audio_bytes
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(audio_bytes)
    return buf.getvalue()


def generate_speech(text, voice=DEFAULT_TTS_VOICE, style="", slow=False):
    """Synthesize lifelike French speech with Gemini TTS and return WAV bytes."""
    if not api_key:
        raise RuntimeError("No API key configured in SECRET.json.")

    clean_text = (text or "").strip()
    if not clean_text:
        raise ValueError("Empty text for speech synthesis.")

    valid_voices = {v for v, _ in TTS_VOICES}
    chosen_voice = voice if voice in valid_voices else DEFAULT_TTS_VOICE

    if not style:
        style = (
            "native French speaker, speaking slowly, clearly, and distinctly for dictation"
            if slow
            else "warm, natural native French speaker, expressive and human-like"
        )

    cache_key = (clean_text, chosen_voice, style)
    if cache_key in _TTS_CACHE:
        _TTS_CACHE.move_to_end(cache_key)
        return _TTS_CACHE[cache_key]

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    last_error = None

    # 1. Try Gemini 3.8 TTS Interactions API (returns WAV by default)
    for tts_model in TTS_MODELS_INTERACTIONS:
        try:
            resp = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                headers=headers,
                json={
                    "model": tts_model,
                    "input": [{
                        "type": "user_input",
                        "content": [{
                            "type": "text",
                            "text": clean_text,
                            "annotations": [{
                                "type": "speech_metadata",
                                "style": style,
                            }],
                        }],
                    }],
                    "response_format": {"type": "audio"},
                    "generation_config": {
                        "speech_config": [{"voice": chosen_voice}]
                    },
                },
                timeout=25,
            )
            if resp.status_code == 200:
                payload = resp.json()
                for step in reversed(payload.get("steps", [])):
                    if step.get("type") == "model_output":
                        for item in reversed(step.get("content", [])):
                            if item.get("type") == "audio" and item.get("data"):
                                wav_bytes = _ensure_wav(base64.b64decode(item["data"]))
                                _TTS_CACHE[cache_key] = wav_bytes
                                if len(_TTS_CACHE) > _TTS_CACHE_MAX:
                                    _TTS_CACHE.popitem(last=False)
                                return wav_bytes
            else:
                last_error = f"{tts_model}: HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)

    # 2. Fallback: Gemini generateContent TTS endpoint (returns L16 PCM or WAV)
    spoken_prompt = (
        f"Speak this French text slowly and clearly: {clean_text}"
        if slow
        else clean_text
    )
    for tts_model in TTS_MODELS_GENERATE:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{tts_model}:generateContent",
                headers=headers,
                json={
                    "contents": [{"parts": [{"text": spoken_prompt}]}],
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {
                            "voiceConfig": {
                                "prebuiltVoiceConfig": {"voiceName": chosen_voice}
                            }
                        },
                    },
                },
                timeout=25,
            )
            if resp.status_code == 200:
                payload = resp.json()
                parts = (
                    payload.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [])
                )
                for part in parts:
                    inline = part.get("inlineData") or {}
                    if inline.get("data"):
                        wav_bytes = _ensure_wav(base64.b64decode(inline["data"]))
                        _TTS_CACHE[cache_key] = wav_bytes
                        if len(_TTS_CACHE) > _TTS_CACHE_MAX:
                            _TTS_CACHE.popitem(last=False)
                        return wav_bytes
            else:
                last_error = f"{tts_model}: HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)

    raise RuntimeError(f"TTS synthesis failed ({last_error})")
