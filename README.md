# Voice Journal - AI-Powered Voice Journaling with Redis Agent Memory Server

A voice-based journaling application using Sarvam AI for speech-to-text and **Redis Agent Memory Server** for intelligent memory management and semantic search.

## Project Status

**Phase 1 Complete:** Architecture design with Agent Memory Server integration
**Current Phase:** Ready for implementation

## What is Voice Journal?

Voice Journal lets you:
- Speak your journal entries instead of typing
- Search past entries by meaning using semantic search
- Maintain conversation context across sessions with automatic memory extraction
- Support 22 Indian languages plus English
- Store everything in Redis Agent Memory Server for intelligent memory management

## Architecture

```
Voice Input -> Sarvam STT -> Journal Engine -> Agent Memory Server
                                            -> Working Memory (session-scoped)
                                            -> Long-term Memory (persistent)
                                            -> Automatic topic extraction
                                            -> Entity recognition
```

See the [Architecture Document](VOICE_JOURNAL_PLAN.md) and [Agent Memory Integration](AGENT_MEMORY_INTEGRATION.md) for details.

## Quick Test - Sarvam STT API

### Prerequisites

1. **Python 3.9+** installed
2. **PortAudio** library (required for PyAudio microphone access)

```bash
# macOS
brew install portaudio

# Linux
sudo apt-get install portaudio19-dev
```

### Test the STT API

1. **Install dependencies:**
```bash
pip3 install sarvamai pyaudio
```

2. **Run the test script:**
```bash
python3 test_sarvam_stt.py
```

The script will:
- Give you a 3-second countdown
- Record 5 seconds of audio from your microphone
- Transcribe using Sarvam AI Saaras v3
- Display the transcribed text with language detection

## Project Documentation

- **[VOICE_JOURNAL_PLAN.md](VOICE_JOURNAL_PLAN.md)** - Complete architecture with Agent Memory Server
- **[AGENT_MEMORY_INTEGRATION.md](AGENT_MEMORY_INTEGRATION.md)** - Why and how we use Agent Memory Server
- **[IMPLEMENTATION_ROADMAP_AGENT_MEMORY.md](IMPLEMENTATION_ROADMAP_AGENT_MEMORY.md)** - Implementation steps with Agent Memory Server
- **[QUICK_START.md](QUICK_START.md)** - Quick start guide and usage examples

## Implementation Plan

### Completed
- [x] Architecture design
- [x] Redis schema design
- [x] Module breakdown
- [x] STT API testing

### Next Steps
- [ ] Set up Redis integration
- [ ] Build core journal module
- [ ] Implement working memory system
- [ ] Add semantic search with vector embeddings
- [ ] Build CLI interface
- [ ] Add multi-language support
- [ ] Implement analytics
- [ ] Testing and documentation

See [Task List](#task-list) below for details.

## Key Features

### 1. Voice Recording & Transcription
- Record via microphone
- Sarvam Saaras v3 STT (22 languages)
- Multiple modes: transcribe, translate, verbatim, translit, codemix

### 2. Redis Agent Memory Server
- **Working Memory**: Session-scoped messages and context
- **Long-term Memory**: Automatically extracted facts and preferences
- **Automatic Topic Extraction**: Identifies topics across entries
- **Entity Recognition**: Tracks people, places, events
- **Conversation Summarization**: Automatic summaries
- **Deduplication**: Prevents redundant memories

### 3. Semantic Search
- Built-in vector embeddings via Agent Memory Server
- HNSW algorithm for fast approximate search
- Metadata filtering (user, date, topic, entity)

### 4. Multi-language Support
- 22 Indian languages
- Automatic language detection
- Code-mixing support
- Translation mode

## Memory Architecture

Using Redis Agent Memory Server:

```
Working Memory (Session-scoped)          Long-term Memory (Persistent)
├── Messages (journal entries)           ├── Semantic memories (facts)
├── Structured memories                  ├── Episodic memories (events)
├── Summary of past messages             ├── Preferences (user settings)
└── Metadata (session info)              ├── Topics (auto-extracted)
                                         ├── Entities (people, places)
                                         └── Vector embeddings (search)

Additional Storage (Redis):
├── journal:audio:{user_id}:{entry_id} -> JSON (audio metadata)
└── user:prefs:{user_id}               -> Hash (user settings)
```

## Technology Stack

- **Sarvam AI** - Speech-to-text (Saaras v3)
- **Redis Agent Memory Server** - Working and long-term memory management
- **agent-memory-client** - Python client for Agent Memory Server
- **Redis 7.4+** - Backend for Agent Memory Server + audio metadata
- **Python 3.9+** - Runtime

## Task List

1. [x] **Design Voice Journal Architecture** - Complete
2. [ ] **Set up Redis Integration** - Install Redis, design schema, implement CRUD
3. [ ] **Build Core Voice Journal Module** - Recording, transcription, storage
4. [ ] **Implement Working Memory System** - Session management, context tracking
5. [ ] **Add Semantic Search** - Vector embeddings, Redis vector index
6. [ ] **Build Conversation Interface** - CLI with commands
7. [ ] **Add Journal Entry Management** - CRUD operations
8. [ ] **Implement Multi-language Support** - 22 languages, auto-detection
9. [ ] **Add Analytics and Insights** - Statistics, trends, patterns
10. [ ] **Testing and Documentation** - Tests, docs, error handling

**Estimated Time:** 25-35 hours total

## Environment Variables

```bash
SARVAM_API_KEY=sk_0kh9urbr_zlWYVksa7nTw98jGnGT3LOuZ
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

## Redis Best Practices Applied

- Connection pooling for efficiency
- Consistent key naming: `entity:type:id`
- TTL on sessions (30 minutes)
- JSON for nested data, Hash for flat data
- Sorted Sets for timeline indexing
- HNSW vector search for semantic queries
- Memory limits and eviction policies

## Contributing

This is a demonstration project. Feel free to fork and extend!
