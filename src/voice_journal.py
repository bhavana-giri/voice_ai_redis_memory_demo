"""Main Voice Journal class integrating STT, TTS, and Memory."""
import os
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

from .audio_handler import AudioHandler
from .memory_client import MemoryClient

load_dotenv()


class VoiceJournal:
    """
    Voice Journal with Redis Agent Memory Server.
    
    Combines:
    - Sarvam AI STT (Saaras v3) for speech-to-text
    - Sarvam AI TTS (Bulbul v3) for text-to-speech
    - Redis Agent Memory Server for conversation memory
    """
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        tts_enabled: bool = True,
        tts_language: str = "en-IN",
        tts_speaker: str = "shubh"
    ):
        self.user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.audio = AudioHandler()
        self.memory = MemoryClient()
        
        self.tts_enabled = tts_enabled
        self.tts_language = tts_language
        self.tts_speaker = tts_speaker
        
        self._entries: List[Dict[str, Any]] = []
    
    def speak(self, text: str, language_code: Optional[str] = None):
        """Speak text using TTS if enabled."""
        if self.tts_enabled:
            lang = language_code or self.tts_language
            self.audio.speak(text, lang, self.tts_speaker)
        else:
            print(f"🔊 {text}")
    
    async def record_entry(
        self,
        duration: int = 10,
        stt_mode: str = "transcribe"
    ) -> Dict[str, Any]:
        """
        Record a voice journal entry.
        
        Args:
            duration: Recording duration in seconds
            stt_mode: STT mode (transcribe, translate, verbatim)
            
        Returns:
            Entry dict with transcript and metadata
        """
        # Record audio
        audio_file = self.audio.record_audio(duration=duration)
        
        # Transcribe
        print("🔄 Transcribing...")
        transcript, language_code, request_id = self.audio.transcribe(
            audio_file, mode=stt_mode
        )
        
        print(f"📝 Transcript: {transcript}")
        print(f"🌐 Language: {language_code}")
        
        # Store in memory
        entry = await self.memory.add_journal_entry(
            session_id=self.session_id,
            user_id=self.user_id,
            transcript=transcript,
            language_code=language_code,
            audio_file=audio_file,
            metadata={"stt_mode": stt_mode, "request_id": request_id}
        )
        
        self._entries.append(entry)
        return entry
    
    async def respond(self, response_text: str, language_code: Optional[str] = None):
        """Add an assistant response and speak it."""
        # Store in memory
        await self.memory.add_assistant_response(
            session_id=self.session_id,
            user_id=self.user_id,
            response=response_text
        )
        
        # Speak response
        self.speak(response_text, language_code)
    
    async def get_history(self) -> List[Dict[str, Any]]:
        """Get conversation history for current session."""
        return await self.memory.get_session_history(
            session_id=self.session_id,
            user_id=self.user_id
        )
    
    async def new_session(self) -> str:
        """Start a new journal session."""
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._entries = []
        return self.session_id
    
    async def end_session(self):
        """End the current session."""
        await self.memory.end_session(self.session_id)
        self._entries = []
    
    async def close(self):
        """Close all connections."""
        await self.memory.close()
    
    @property
    def entries(self) -> List[Dict[str, Any]]:
        """Get entries from current session."""
        return self._entries.copy()
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all components."""
        memory_ok = await self.memory.health_check()
        return {
            "memory_server": memory_ok,
            "sarvam_api": self.audio.client is not None
        }

