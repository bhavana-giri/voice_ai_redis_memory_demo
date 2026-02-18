# Voice Journal Implementation Roadmap (with Redis Agent Memory Server)

## Project Structure

```
voice_ai_redis_memory_demo/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration and environment variables
│   ├── voice_recorder.py         # Audio recording module
│   ├── sarvam_client.py          # Sarvam AI API wrapper
│   ├── memory_client.py          # Agent Memory Server client wrapper
│   ├── audio_storage.py          # Audio metadata storage in Redis
│   ├── journal_engine.py         # Core journal logic
│   └── cli_interface.py          # Command-line interface
├── tests/
│   ├── test_voice_recorder.py
│   ├── test_memory_client.py
│   ├── test_audio_storage.py
│   └── test_journal_engine.py
├── recordings/                   # Stored audio files
├── .env                          # Environment variables (gitignored)
├── requirements.txt              # Python dependencies
├── README.md                     # User documentation
└── main.py                       # Application entry point
```

## Phase 1: Foundation (Tasks 1-3)

### Task 1: Design Voice Journal Architecture
**Status:** Complete
**Deliverables:**
- Architecture document (VOICE_JOURNAL_PLAN.md)
- System diagram
- Agent Memory Server integration design
- Module breakdown

### Task 2: Set up Redis Agent Memory Server
**Duration:** 2-3 hours
**Steps:**
1. Install Redis locally or use Redis Cloud
2. Install and start Agent Memory Server
3. Configure environment variables
4. Test Agent Memory Server connection
5. Verify working memory and long-term memory operations

**Installation:**
```bash
# Install Redis
docker run -d -p 6379:6379 redis:latest

# Install Agent Memory Server
pip install agent-memory-server

# Start Agent Memory Server
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key
agent-memory api --task-backend=asyncio

# Or use Docker
docker run -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379 \
  -e OPENAI_API_KEY=your-key \
  -e DISABLE_AUTH=true \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

**Key Code:**
```python
# memory_client.py
from agent_memory_client import create_memory_client

class MemoryClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.client = None
        self.base_url = base_url
    
    async def initialize(self):
        self.client = await create_memory_client(self.base_url)
    
    async def add_journal_entry(self, user_id, session_id, transcript, metadata):
        # Add journal entry as a message to working memory
        await self.client.add_messages(
            session_id=session_id,
            user_id=user_id,
            messages=[{
                "role": "user",
                "content": transcript,
                "metadata": metadata
            }]
        )
    
    async def search_memories(self, user_id, query, limit=5):
        # Search long-term memories semantically
        results = await self.client.search_long_term_memory(
            text=query,
            user_id=user_id,
            limit=limit
        )
        return results
```

**Testing:**
- Agent Memory Server starts successfully
- Can add messages to working memory
- Can search long-term memories
- Automatic memory extraction works

### Task 3: Build Core Voice Journal Module
**Duration:** 3-4 hours
**Steps:**
1. Enhance `voice_recorder.py` from test script
2. Create `sarvam_client.py` wrapper
3. Create `audio_storage.py` for metadata
4. Build `journal_engine.py` orchestration
5. Implement entry creation flow

**Key Code:**
```python
# journal_engine.py
import uuid
from datetime import datetime

class JournalEngine:
    def __init__(self, memory_client, sarvam_client, recorder, audio_storage):
        self.memory = memory_client
        self.sarvam = sarvam_client
        self.recorder = recorder
        self.audio_storage = audio_storage
    
    async def create_entry(self, user_id, session_id, duration=30):
        # Generate entry ID
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Record audio
        audio_file = self.recorder.record(duration, entry_id)
        
        # Transcribe
        result = self.sarvam.transcribe(audio_file)
        
        # Store audio metadata in Redis
        await self.audio_storage.store_metadata(
            user_id=user_id,
            entry_id=entry_id,
            audio_file_path=audio_file,
            duration_seconds=duration,
            language_code=result.language_code,
            transcript_preview=result.transcript[:100]
        )
        
        # Add to Agent Memory Server as a message
        await self.memory.add_journal_entry(
            user_id=user_id,
            session_id=session_id,
            transcript=result.transcript,
            metadata={
                "entry_id": entry_id,
                "timestamp": timestamp,
                "language_code": result.language_code,
                "mode": "transcribe",
                "duration_seconds": duration,
                "audio_file_path": audio_file
            }
        )
        
        return {
            "entry_id": entry_id,
            "transcript": result.transcript,
            "language_code": result.language_code
        }
```

## Total Estimated Time: 20-30 hours

## Dependencies to Install

```txt
sarvamai>=0.1.0
pyaudio>=0.2.13
agent-memory-server>=0.13.0
agent-memory-client>=0.13.0
redis>=5.0.0
python-dotenv>=1.0.0
```

## Environment Variables

```bash
SARVAM_API_KEY=sk_0kh9urbr_zlWYVksa7nTw98jGnGT3LOuZ
MEMORY_SERVER_URL=http://localhost:8000
OPENAI_API_KEY=your-openai-key
REDIS_URL=redis://localhost:6379
```

