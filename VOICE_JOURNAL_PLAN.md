# Voice Journal with Sarvam AI + Redis Agent Memory Server - Architecture Plan

## Overview

A voice-based journaling application that uses Sarvam AI models for speech-to-text and **Redis Agent Memory Server** for intelligent working memory and persistent storage. Users can speak their journal entries, search past entries semantically, and maintain conversation context across sessions.

## System Architecture

### Components

1. **Voice Input Layer** - Sarvam Saaras v3 STT
2. **Core Journal Engine** - Python application logic
3. **Memory Layer** - Redis Agent Memory Server (working + long-term memory)
4. **Search Layer** - Built-in semantic search via Agent Memory Server
5. **CLI Interface** - Interactive command-line interface

### Data Flow

```
User Speech -> Microphone -> Sarvam STT -> Journal Entry -> Agent Memory Server
                                                          -> Working Memory (session-scoped)
                                                          -> Long-term Memory (persistent)
                                                          -> Automatic topic extraction
                                                          -> Entity recognition

User Query -> Voice/Text -> Agent Memory Server -> Semantic Search -> Relevant Entries
                                                -> Context Retrieval -> Working Memory
```

### Why Redis Agent Memory Server?

Instead of building custom Redis memory management, we use the **Redis Agent Memory Server** which provides:

- **Two-tier memory**: Working memory (session-scoped) + Long-term memory (persistent)
- **Automatic memory extraction**: Converts conversations into structured memories
- **Semantic search**: Built-in vector search with metadata filtering
- **Topic modeling**: Automatic topic extraction from conversations
- **Entity recognition**: Identifies and tracks entities across sessions
- **Conversation summarization**: Automatic summaries of past messages
- **Deduplication**: Prevents redundant memories
- **LangChain integration**: Easy integration with AI frameworks
- **Production-ready**: Authentication, background workers, monitoring

## Memory Architecture with Agent Memory Server

The Redis Agent Memory Server handles all memory management automatically. We only need to:

1. **Send journal entries as messages** to working memory
2. **Let the server extract long-term memories** automatically
3. **Query memories** using semantic search

### Agent Memory Server Structure

```
Working Memory (Session-scoped)          Long-term Memory (Persistent)
├── Messages (journal entries)           ├── Semantic memories (extracted facts)
├── Structured memories                  ├── Episodic memories (events)
├── Summary of past messages             ├── Preferences (user settings)
└── Metadata (session info)              ├── Topics (auto-extracted)
                                         ├── Entities (people, places, things)
                                         └── Vector embeddings (for search)
```

### Journal Entry Storage

We'll store journal entries in two ways:

**1. As Working Memory Messages** (via Agent Memory Server)
```python
await memory_client.add_messages(
    session_id=session_id,
    user_id=user_id,
    messages=[{
        "role": "user",
        "content": transcript,
        "metadata": {
            "entry_id": "uuid",
            "timestamp": "2026-02-16T10:30:00Z",
            "language_code": "en-IN",
            "mode": "transcribe",
            "duration_seconds": 45,
            "audio_file_path": "recordings/uuid.wav"
        }
    }]
)
```

**2. As Long-term Memories** (automatically extracted by server)
The server will automatically:
- Extract key facts and preferences
- Identify topics and entities
- Create semantic embeddings
- Deduplicate similar memories
- Store in Redis with vector index

### Additional Storage for Audio Files

**Audio File Metadata (Redis JSON)** - for quick access to recordings

**Key Pattern:** `journal:audio:{user_id}:{entry_id}`

```json
{
  "entry_id": "uuid",
  "user_id": "user123",
  "timestamp": "2026-02-16T10:30:00Z",
  "audio_file_path": "recordings/2026-02-16_uuid.wav",
  "duration_seconds": 45,
  "language_code": "en-IN",
  "transcript_preview": "Today was a great day..."
}
```

### User Preferences (Redis Hash)

**Key Pattern:** `user:prefs:{user_id}`

```
HSET user:prefs:user123
  default_language "en-IN"
  stt_mode "transcribe"
  recording_duration "30"
  enable_auto_tagging "true"
```

**No TTL** - persistent user settings

## Application Architecture

### Core Modules

#### 1. `voice_recorder.py`
- Record audio from microphone
- Save as WAV (16kHz, mono)
- Handle audio device selection
- Progress feedback

#### 2. `sarvam_client.py`
- Wrapper for Sarvam AI SDK
- STT transcription (multiple modes)
- Error handling and retries
- Rate limiting

#### 3. `memory_client.py`
- Wrapper for Agent Memory Server client
- Add journal entries as messages to working memory
- Search long-term memories semantically
- Retrieve conversation context
- Session management

#### 4. `audio_storage.py`
- Store audio file metadata in Redis JSON
- Manage audio file paths
- Retrieve audio files by entry ID
- Timeline indexing for chronological access

#### 5. `journal_engine.py`
- Main application logic
- Orchestrate recording -> transcription -> memory storage
- Context management via Agent Memory Server
- Entry retrieval and search

#### 6. `cli_interface.py`
- Interactive command-line interface
- Command parsing (new, search, review, stats)
- Display formatting
- User prompts

### Configuration

`config.py`:
```python
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

# Agent Memory Server configuration
MEMORY_SERVER_URL = os.getenv("MEMORY_SERVER_URL", "http://localhost:8000")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # For embeddings in Agent Memory Server

# Redis configuration (for audio metadata storage)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Recording settings
RECORDING_DURATION = 30  # seconds
SAMPLE_RATE = 16000
CHANNELS = 1
```

## Features

### Phase 1: Core Functionality
- Record voice journal entries
- Transcribe with Sarvam STT
- Store in Agent Memory Server as messages
- Automatic long-term memory extraction
- Retrieve entries by date

### Phase 2: Semantic Search
- Search journal entries by meaning (via Agent Memory Server)
- Topic-based retrieval
- Entity-based search (people, places, events)
- Date range filtering

### Phase 3: Advanced Features
- Multi-language support (22 languages)
- Translation mode for reviewing entries
- Conversation summaries (automatic via Agent Memory Server)
- Mood/sentiment tracking
- Analytics dashboard

### Phase 4: AI-Powered Insights
- Automatic topic extraction (via Agent Memory Server)
- Entity recognition across entries
- Memory deduplication
- Preference learning
- Personalized prompts based on past entries

## Redis Best Practices Applied

1. **Agent Memory Server**: Production-ready memory management with automatic extraction
2. **Data Structures**: JSON for audio metadata, Hash for user preferences
3. **Key Naming**: Consistent pattern `entity:type:id:attribute`
4. **Memory Management**: Automatic TTL and eviction via Agent Memory Server
5. **Vector Search**: Built-in HNSW algorithm via Agent Memory Server
6. **Semantic Search**: Automatic embedding generation and indexing
7. **Security**: OAuth2/JWT authentication via Agent Memory Server

## Technology Stack

- **Python 3.9+**
- **Sarvam AI SDK** - Speech-to-text
- **Redis Agent Memory Server** - Working and long-term memory management
- **agent-memory-client** - Python client for Agent Memory Server
- **Redis 7.4+** - Backend for Agent Memory Server + audio metadata
- **redis-py** - Redis client for audio metadata storage
- **PyAudio** - Microphone access
- **python-dotenv** - Environment variables

## Next Steps

1. Design Voice Journal Architecture (CURRENT)
2. Set up Redis Agent Memory Server
3. Build Core Voice Journal Module
4. Integrate with Agent Memory Server
5. Add Audio Metadata Storage
6. Build Conversation Interface
7. Add Journal Entry Management
8. Implement Multi-language Support
9. Add Analytics and Insights
10. Testing and Documentation

