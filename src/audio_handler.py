"""Audio handling for STT and TTS using Sarvam AI."""
import os
import wave
import base64
import tempfile
import subprocess
from datetime import datetime
from typing import Optional, Tuple
import pyaudio
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError
from dotenv import load_dotenv

load_dotenv()


class AudioHandler:
    """Handles audio recording, STT, and TTS using Sarvam AI."""
    
    # Audio recording settings
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # 16kHz for speech
    CHUNK = 1024
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SARVAM_API_KEY")
        self.client = SarvamAI(api_subscription_key=self.api_key)
        self.recordings_dir = "recordings"
        os.makedirs(self.recordings_dir, exist_ok=True)
    
    def record_audio(self, duration: int = 5, show_countdown: bool = True) -> str:
        """
        Record audio from microphone.
        
        Args:
            duration: Recording duration in seconds
            show_countdown: Whether to show countdown before recording
            
        Returns:
            Path to the recorded audio file
        """
        if show_countdown:
            import time
            print(f"\n🎤 Recording will start in 3 seconds...")
            for i in range(3, 0, -1):
                print(f"⏳ {i}...")
                time.sleep(1)
        
        print(f"🔴 RECORDING ({duration}s) - Speak now!")
        
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        frames = []
        for i in range(0, int(self.RATE / self.CHUNK * duration)):
            data = stream.read(self.CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        audio.terminate()
        
        # Save to file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.recordings_dir, f"recording_{timestamp}.wav")
        
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(audio.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(frames))
        
        print(f"✅ Recording saved: {filename}")
        return filename
    
    def transcribe(
        self, 
        audio_file: str, 
        mode: str = "transcribe",
        language_code: Optional[str] = None
    ) -> Tuple[str, str, str]:
        """
        Transcribe audio using Sarvam AI Saaras v3.
        
        Args:
            audio_file: Path to audio file
            mode: transcribe, translate, verbatim, or transliterate
            language_code: Optional language code hint
            
        Returns:
            Tuple of (transcript, language_code, request_id)
        """
        try:
            with open(audio_file, "rb") as f:
                kwargs = {"file": f, "model": "saaras:v3", "mode": mode}
                if language_code:
                    kwargs["language_code"] = language_code
                response = self.client.speech_to_text.transcribe(**kwargs)
            
            return response.transcript, response.language_code, response.request_id
            
        except ApiError as e:
            raise Exception(f"STT API Error {e.status_code}: {e.body}")
    
    def text_to_speech(
        self,
        text: str,
        language_code: str = "en-IN",
        speaker: str = "shubh"
    ) -> bytes:
        """
        Convert text to speech using Sarvam AI Bulbul v3.
        
        Args:
            text: Text to convert (max 1500 chars)
            language_code: Target language code
            speaker: Speaker voice name
            
        Returns:
            Audio bytes (WAV format)
        """
        if len(text) > 1500:
            text = text[:1500]  # Truncate to max length
        
        response = self.client.text_to_speech.convert(
            target_language_code=language_code,
            text=text,
            model="bulbul:v3",
            speaker=speaker
        )
        
        audio_base64 = response.audios[0]
        return base64.b64decode(audio_base64)
    
    def speak(self, text: str, language_code: str = "en-IN", speaker: str = "shubh"):
        """Convert text to speech and play it."""
        audio_bytes = self.text_to_speech(text, language_code, speaker)
        
        # Save to temp file and play
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            subprocess.run(["afplay", temp_path], check=True, capture_output=True)
        except Exception:
            print(f"[Audio saved to {temp_path}]")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

