import os
import requests
import tempfile
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def transcribe_audio(file_input, prompt=None):
    """
    Transcribes audio from a local file path or a URL using OpenAI Whisper API.
    """
    if not OPENAI_API_KEY or "your_openai" in OPENAI_API_KEY:
        raise Exception("OpenAI API Key is missing or invalid. Please check .env file.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    temp_file = None
    try:
        # Check if input is a URL
        if file_input.startswith(("http://", "https://")):
            print(f"DEBUG: Downloading audio from {file_input}")
            r = requests.get(file_input)
            if r.status_code != 200:
                raise Exception(f"Failed to download audio: {r.status_code}")
            
            # Create a temporary file to hold the downloaded audio
            suffix = ".wav" if ".wav" in file_input.lower() else ".m4a"
            fd, temp_path = tempfile.mkstemp(suffix=suffix)
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(r.content)
            file_to_open = temp_path
            temp_file = temp_path
        else:
            file_to_open = file_input

        if not os.path.exists(file_to_open):
            raise Exception(f"Audio file not found: {file_to_open}")

        with open(file_to_open, "rb") as audio_file:
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
    finally:
        # Cleanup temp file if created
        if temp_file and os.path.exists(temp_file):
            try: os.remove(temp_file)
            except: pass
