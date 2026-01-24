import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_path, prompt=None):
    """
    Transcribes audio file using OpenAI Whisper API.
    """
    if not OPENAI_API_KEY or "your_openai" in OPENAI_API_KEY:
        raise Exception("OpenAI API Key is missing or invalid. Please check .env file.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    try:
        with open(file_path, "rb") as audio_file:
            files = {
                "file": audio_file,
                "model": (None, "whisper-1")
            }
            if prompt:
                files["prompt"] = (None, prompt)
                
            response = requests.post(url, headers=headers, files=files)
            
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            error_data = response.json()
            raise Exception(f"Whisper API Error: {error_data.get('error', {}).get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"Transcription Error: {e}")
        raise e
