# Redis Agent Memory Server Integration

## Why Agent Memory Server?

Instead of building custom Redis memory management, we're using the **Redis Agent Memory Server** - a production-ready memory layer for AI agents.

## Key Benefits

### 1. Automatic Memory Management
- **No manual memory extraction**: Server automatically extracts facts, preferences, and entities from conversations
- **Two-tier memory**: Working memory (session-scoped) + Long-term memory (persistent)
- **Automatic deduplication**: Prevents redundant memories
- **Topic modeling**: Automatically identifies topics across entries

### 2. Built-in Semantic Search
- **Vector embeddings**: Automatic generation and indexing
- **HNSW algorithm**: Fast approximate search
- **Metadata filtering**: Filter by user, date, topic, entity
- **No manual vector index management**: Server handles everything

### 3. Production-Ready Features
- **Authentication**: OAuth2/JWT support
- **Background workers**: Async task processing
- **Monitoring**: Built-in observability
- **Multi-provider LLM**: OpenAI, Anthropic, AWS Bedrock, Ollama

### 4. Easy Integration
- **Python SDK**: Simple async client
- **LangChain integration**: Automatic tool conversion
- **MCP support**: Model Context Protocol for AI agents

## Architecture Comparison

### Before (Custom Redis)
```
Voice Input -> STT -> Custom Redis Memory Manager
                   -> Manual embedding generation
                   -> Manual vector index creation
                   -> Manual session management
                   -> Manual TTL handling
```

### After (Agent Memory Server)
```
Voice Input -> STT -> Agent Memory Server
                   -> Automatic memory extraction
                   -> Automatic embedding generation
                   -> Automatic vector indexing
                   -> Automatic session management
                   -> Built-in semantic search
```

## How It Works for Voice Journal

### 1. Recording a Journal Entry
```python
# Record and transcribe
audio_file = recorder.record(30)
result = sarvam.transcribe(audio_file)

# Add to Agent Memory Server as a message
await memory_client.add_messages(
    session_id=session_id,
    user_id=user_id,
    messages=[{
        "role": "user",
        "content": result.transcript,
        "metadata": {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "language_code": result.language_code,
            "audio_file_path": audio_file
        }
    }]
)

# Server automatically:
# - Stores in working memory
# - Extracts long-term memories
# - Generates embeddings
# - Identifies topics and entities
# - Deduplicates similar memories
```

### 2. Searching Journal Entries
```python
# Semantic search
results = await memory_client.search_long_term_memory(
    text="What did I do last week about work?",
    user_id=user_id,
    limit=5
)

# Server automatically:
# - Generates query embedding
# - Performs vector similarity search
# - Filters by user_id
# - Returns relevant memories with scores
```

### 3. Getting Conversation Context
```python
# Get working memory for context
context = await memory_client.get_working_memory(
    session_id=session_id,
    user_id=user_id
)

# Returns:
# - Recent messages
# - Conversation summary
# - Relevant long-term memories
# - Session metadata
```

## What We Still Need to Build

### 1. Audio File Storage
Agent Memory Server handles text memories, but we need to store audio files separately:
- Audio file metadata in Redis JSON
- Timeline indexing for chronological access
- Audio file path management

### 2. User Preferences
Store user-specific settings:
- Default language
- Recording duration
- STT mode preferences

### 3. Application Logic
- Voice recording interface
- Sarvam STT integration
- CLI interface
- Entry management (CRUD)

## Installation

```bash
# Install Agent Memory Server
pip install agent-memory-server agent-memory-client

# Start Redis
docker run -d -p 6379:6379 redis:latest

# Start Agent Memory Server
export REDIS_URL=redis://localhost:6379
export OPENAI_API_KEY=your-key
export DISABLE_AUTH=true  # For development only
agent-memory api --task-backend=asyncio
```

## Configuration

```bash
# .env file
SARVAM_API_KEY=sk_0kh9urbr_zlWYVksa7nTw98jGnGT3LOuZ
MEMORY_SERVER_URL=http://localhost:8000
OPENAI_API_KEY=your-openai-key
REDIS_URL=redis://localhost:6379
```

## Next Steps

1. [x] Design architecture with Agent Memory Server
2. [ ] Install and configure Agent Memory Server
3. [ ] Build memory_client.py wrapper
4. [ ] Integrate with journal_engine.py
5. [ ] Test automatic memory extraction
6. [ ] Build audio metadata storage
7. [ ] Implement CLI interface

## Resources

- [Agent Memory Server GitHub](https://github.com/redis/agent-memory-server)
- [Documentation](https://redis.github.io/agent-memory-server/)
- [Python SDK](https://redis.github.io/agent-memory-server/python-sdk/)
- [LangChain Integration](https://redis.github.io/agent-memory-server/langchain-integration/)

