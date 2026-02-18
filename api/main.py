"""FastAPI backend for Voice Journal UI."""
import os
import sys
import base64
import tempfile
import uuid
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

from src.audio_handler import AudioHandler
from src.journal_manager import JournalManager
from src.analytics import JournalAnalytics
from src.memory_client import MemoryClient
from src.voice_agent import VoiceJournalAgent

# Global clients
memory_client: Optional[MemoryClient] = None
agents: Dict[str, VoiceJournalAgent] = {}  # user_id -> agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global memory_client
    memory_client = MemoryClient()

    # Check memory server health
    is_healthy = await memory_client.health_check()
    if is_healthy:
        print("[OK] Connected to Redis Agent Memory Server")
    else:
        print("[WARN] Redis Agent Memory Server not available - memory features disabled")

    yield
    # Cleanup
    if memory_client:
        await memory_client.close()

app = FastAPI(title="Voice Journal API", version="1.0.0", lifespan=lifespan)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
audio_handler = AudioHandler()
journal_manager = JournalManager()
analytics = JournalAnalytics()


class TranscribeRequest(BaseModel):
    audio_base64: str
    language_code: Optional[str] = None
    session_id: Optional[str] = None
    user_id: str = "default_user"
    store_in_memory: bool = True


class EntryCreate(BaseModel):
    transcript: str
    language_code: str = "en-IN"
    duration_seconds: float
    mood: Optional[str] = None
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    user_id: str = "default_user"


class EntryUpdate(BaseModel):
    transcript: Optional[str] = None
    mood: Optional[str] = None
    tags: Optional[List[str]] = None


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    memory_healthy = await memory_client.health_check() if memory_client else False
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "memory_server": memory_healthy
    }


@app.post("/api/transcribe")
async def transcribe_audio(request: TranscribeRequest):
    """Transcribe audio using Sarvam AI and store in memory."""
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(request.audio_base64)

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            transcript, language_code, request_id = audio_handler.transcribe(
                temp_path,
                language_code=request.language_code
            )

            # Generate session ID if not provided
            session_id = request.session_id or str(uuid.uuid4())

            # Store in Redis Agent Memory Server (long-term memory for retrieval)
            memory_entry = None
            if request.store_in_memory and memory_client:
                try:
                    memory_entry = await memory_client.create_journal_memory(
                        user_id=request.user_id,
                        transcript=transcript,
                        language_code=language_code,
                        topics=["journal", "voice_entry"],
                        session_id=session_id
                    )
                    print(f"[OK] Stored voice entry in long-term memory: {memory_entry.get('memory_id', 'unknown')}")
                except Exception as mem_err:
                    print(f"[WARN] Failed to store in memory: {mem_err}")

            return {
                "transcript": transcript,
                "language_code": language_code,
                "request_id": request_id,
                "session_id": session_id,
                "stored_in_memory": memory_entry is not None,
                "memory_entry": memory_entry
            }
        finally:
            os.unlink(temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tts")
def text_to_speech(text: str, language_code: str = "en-IN", speaker: str = "shubh"):
    """Convert text to speech using Sarvam AI."""
    try:
        audio_bytes = audio_handler.text_to_speech(text, language_code, speaker)
        return {"audio_base64": base64.b64encode(audio_bytes).decode()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entries")
def list_entries(user_id: str = "default_user", limit: int = 50):
    """List journal entries."""
    entries = journal_manager.list_entries(user_id, limit=limit)
    return {"entries": entries, "total": len(entries)}


@app.get("/api/entries/{entry_id}")
def get_entry(entry_id: str):
    """Get a specific entry."""
    entry = journal_manager.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@app.post("/api/entries")
async def create_entry(entry: EntryCreate):
    """Create a new journal entry and store in memory."""
    # Generate session ID if not provided
    session_id = entry.session_id or str(uuid.uuid4())

    # Store in Redis Agent Memory Server
    if memory_client:
        try:
            await memory_client.add_journal_entry(
                session_id=session_id,
                user_id=entry.user_id,
                transcript=entry.transcript,
                language_code=entry.language_code,
                metadata={
                    "mood": entry.mood,
                    "tags": entry.tags,
                    "duration_seconds": entry.duration_seconds,
                    "source": "manual_entry"
                }
            )
            print(f"[OK] Stored entry in memory: {session_id}")
        except Exception as mem_err:
            print(f"[WARN] Failed to store in memory: {mem_err}")

    # Also store in journal manager for local persistence
    new_entry = journal_manager.create_entry(
        user_id=entry.user_id,
        transcript=entry.transcript,
        language_code=entry.language_code,
        mood=entry.mood,
        tags=entry.tags
    )
    new_entry["session_id"] = session_id
    return new_entry


@app.get("/api/memory/session/{session_id}")
async def get_session_history(session_id: str, user_id: str = "default_user"):
    """Get conversation history from memory for a session."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Memory server not available")

    try:
        history = await memory_client.get_session_history(session_id, user_id)
        return {"session_id": session_id, "messages": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/memory/session/{session_id}")
async def end_session(session_id: str):
    """End a session and cleanup working memory."""
    if not memory_client:
        raise HTTPException(status_code=503, detail="Memory server not available")

    try:
        await memory_client.end_session(session_id)
        return {"status": "session_ended", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/entries/{entry_id}")
def update_entry(entry_id: str, entry: EntryUpdate):
    """Update a journal entry."""
    updated = journal_manager.update_entry(
        entry_id,
        transcript=entry.transcript,
        mood=entry.mood,
        tags=entry.tags
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Entry not found")
    return updated


@app.delete("/api/entries/{entry_id}")
def delete_entry(entry_id: str):
    """Delete a journal entry."""
    success = journal_manager.delete_entry(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "deleted"}


@app.get("/api/analytics")
def get_analytics(user_id: str = "default_user"):
    """Get analytics for user."""
    return {
        "summary": analytics.get_activity_summary(user_id, days=30),
        "streak": analytics.get_streak(user_id),
        "insights": analytics.generate_insights(user_id),
        "language_distribution": analytics.get_language_distribution(user_id),
        "mood_distribution": analytics.get_mood_distribution(user_id)
    }


# ============ AGENT ENDPOINTS ============

class AgentChatRequest(BaseModel):
    """Request for agent chat endpoint."""
    text: Optional[str] = None
    audio_base64: Optional[str] = None
    user_id: str = "default_user"
    language_code: Optional[str] = None


class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint."""
    response: str
    intent: str
    mode: str
    audio_base64: Optional[str] = None
    entry_count: int
    transcribed_text: Optional[str] = None  # For debugging STT = 0


def get_or_create_agent(user_id: str) -> VoiceJournalAgent:
    """Get or create an agent for a user."""
    if user_id not in agents:
        # Pass memory_client for searching long-term memory (memory_idx)
        agents[user_id] = VoiceJournalAgent(user_id=user_id, memory_client=memory_client)
    return agents[user_id]


@app.post("/api/agent/chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest):
    """
    Main agent endpoint for voice journal interaction.

    Accepts either text or audio input.
    Returns response text and optional TTS audio.
    """
    text = request.text

    transcribed_text = None  # Track what was transcribed from audio

    # If audio provided, transcribe first
    if request.audio_base64 and not text:
        try:
            audio_data = base64.b64decode(request.audio_base64)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_data)
                temp_path = f.name

            try:
                transcript, lang_code, _ = audio_handler.transcribe(
                    temp_path, language_code=request.language_code
                )
                text = transcript
                transcribed_text = transcript
                print(f"[STT] Transcribed: '{transcript}' (lang: {lang_code})")
            finally:
                os.unlink(temp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Audio transcription failed: {e}")

    if not text:
        raise HTTPException(status_code=400, detail="Either text or audio_base64 is required")

    # Get agent and process
    agent = get_or_create_agent(request.user_id)

    try:
        response_text, _ = await agent.process_input(text)

        # Get TTS audio for response
        audio_base64 = None
        try:
            audio_bytes = audio_handler.text_to_speech(response_text, "en-IN", "shubh")
            audio_base64 = base64.b64encode(audio_bytes).decode()
        except Exception as tts_err:
            print(f"TTS failed: {tts_err}")

        # Get current entry count
        entry_count = agent.store.get_entry_count(request.user_id)

        # Get intent safely
        intent_result = agent.intent_detector._rule_based_detect(text)
        intent_str = intent_result.intent.value if intent_result else "unknown"

        return AgentChatResponse(
            response=response_text,
            intent=intent_str,
            mode=agent.get_mode(),
            audio_base64=audio_base64,
            entry_count=entry_count,
            transcribed_text=transcribed_text
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/agent/mode")
def get_agent_mode(user_id: str = "default_user"):
    """Get current agent mode."""
    agent = get_or_create_agent(user_id)
    return {"mode": agent.get_mode(), "user_id": user_id}


@app.post("/api/agent/mode")
def set_agent_mode(user_id: str = "default_user", mode: str = "log"):
    """Set agent mode (log or chat)."""
    if mode not in ("log", "chat"):
        raise HTTPException(status_code=400, detail="Mode must be 'log' or 'chat'")

    agent = get_or_create_agent(user_id)
    agent.set_mode(mode)
    return {"mode": agent.get_mode(), "user_id": user_id}



