# Voice Journal - Quick Start Guide

## What is Voice Journal?

A voice-based journaling application that lets you:
- Speak your journal entries instead of typing
- Search past entries by meaning, not just keywords
- Maintain conversation context across sessions
- Support 22 Indian languages plus English
- Store everything in Redis for fast access

## Architecture Overview

**Voice Input** -> Sarvam STT -> **Journal Engine** -> Redis Storage
                                                    -> Vector Search
                                                    -> Working Memory

## Key Features

### 1. Voice Recording
- Record journal entries via microphone
- Automatic transcription using Sarvam Saaras v3
- Support for multiple languages and code-mixing

### 2. Redis-Backed Memory
- **Journal Entries**: Stored as JSON with full metadata
- **Working Memory**: Recent context with 30-minute TTL
- **Timeline Index**: Chronological entry access
- **User Preferences**: Persistent settings

### 3. Semantic Search
- Find entries by meaning, not exact words
- Vector embeddings for similarity search
- Hybrid search with date/language filters

### 4. Multi-language Support
- 22 Indian languages (Hindi, Tamil, Telugu, etc.)
- Automatic language detection
- Translation mode for reviewing entries

## Redis Schema Summary

```
journal:entry:{user_id}:{entry_id}     -> JSON (entry data + embedding)
session:context:{user_id}:{session_id} -> Hash (working memory, TTL 30min)
user:prefs:{user_id}                   -> Hash (user settings)
journal:timeline:{user_id}             -> Sorted Set (chronological index)
stats:lang:{user_id}                   -> Hash (language usage counts)
idx:journal_entries                    -> Vector Index (semantic search)
```

## Usage Example

```bash
# Start the voice journal
python main.py

# Commands:
> new              # Record a new journal entry
> search happy     # Find entries about happiness
> review today     # Review today's entries
> stats            # Show statistics
> exit             # Exit application
```

## Sample Workflow

1. **Create Entry**
   ```
   > new
   [Recording starts in 3 seconds...]
   [Recording... speak now]
   [Transcribed: "Today I completed my project..."]
   [Saved entry #123]
   ```

2. **Search Entries**
   ```
   > search project completion
   [Found 3 similar entries:]
   1. 2026-02-15: "Today I completed my project..."
   2. 2026-02-10: "Working on the final phase..."
   3. 2026-02-05: "Started new project at work..."
   ```

3. **Review by Date**
   ```
   > review 2026-02-15
   [3 entries on 2026-02-15:]
   - 10:30 AM (en-IN): "Today I completed my project..."
   - 2:15 PM (hi-IN): "आज बहुत अच्छा दिन था..."
   - 8:00 PM (en-IN): "Reflecting on today's achievements..."
   ```

## Redis Best Practices Applied

1. **Connection Pooling**: Reuse connections for efficiency
2. **Key Naming**: Consistent pattern `entity:type:id`
3. **TTL Management**: 30-minute expiration on sessions
4. **Data Structures**: 
   - JSON for nested entry data
   - Hash for flat session/preference data
   - Sorted Set for timeline indexing
5. **Vector Search**: HNSW algorithm for fast semantic search
6. **Memory Limits**: Configure maxmemory and eviction policy

## Technology Stack

- **Sarvam AI**: Speech-to-text (Saaras v3)
- **Redis**: Memory and storage layer
- **RedisVL**: Vector search capabilities
- **sentence-transformers**: Generate embeddings
- **Python 3.9+**: Application runtime

## Development Phases

- [x] Phase 1: Architecture Design
- [ ] Phase 2: Redis Integration
- [ ] Phase 3: Core Journal Module
- [ ] Phase 4: Working Memory System
- [ ] Phase 5: Semantic Search
- [ ] Phase 6: CLI Interface
- [ ] Phase 7: Multi-language Support
- [ ] Phase 8: Analytics
- [ ] Phase 9: Testing & Documentation

## Next Steps

1. Install Redis (local or cloud)
2. Set up Python environment
3. Install dependencies
4. Configure environment variables
5. Start building!

See IMPLEMENTATION_ROADMAP.md for detailed steps.

## Benefits

### For Users
- Faster journaling (speak vs type)
- Natural language search
- Multi-language support
- Context-aware experience

### Technical Benefits
- Redis speed (sub-millisecond access)
- Scalable architecture
- Semantic search capabilities
- Session management with TTL
- Vector similarity search

## Performance Characteristics

- **Entry Creation**: ~2-3 seconds (recording + transcription)
- **Search**: <100ms (vector search with HNSW)
- **Context Retrieval**: <10ms (Redis hash/sorted set)
- **Storage**: ~2KB per entry (JSON + embedding)

## Security Considerations

- Store API keys in environment variables
- Use Redis authentication in production
- Implement ACLs for fine-grained access
- Enable TLS for Redis connections
- Sanitize user inputs

## Monitoring

Track these Redis metrics:
- `used_memory`: Current memory usage
- `connected_clients`: Active connections
- `keyspace_hits/misses`: Cache hit ratio
- `instantaneous_ops_per_sec`: Throughput

## Future Enhancements

- Voice output (TTS) for reading entries
- Mobile app integration
- Cloud sync across devices
- Mood tracking and sentiment analysis
- AI-powered insights and summaries
- Export to PDF/Markdown
- Collaborative journaling
- End-to-end encryption

