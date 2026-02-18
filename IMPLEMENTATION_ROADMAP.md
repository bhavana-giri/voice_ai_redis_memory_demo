# Voice Journal Implementation Roadmap

## Project Structure

```
voice_ai_redis_memory_demo/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration and environment variables
│   ├── voice_recorder.py         # Audio recording module
│   ├── sarvam_client.py          # Sarvam AI API wrapper
│   ├── redis_memory.py           # Redis operations and memory management
│   ├── vector_search.py          # Embedding generation and vector search
│   ├── journal_engine.py         # Core journal logic
│   └── cli_interface.py          # Command-line interface
├── tests/
│   ├── test_voice_recorder.py
│   ├── test_redis_memory.py
│   ├── test_vector_search.py
│   └── test_journal_engine.py
├── recordings/                   # Stored audio files
├── .env                          # Environment variables (gitignored)
├── requirements.txt              # Python dependencies
├── README.md                     # User documentation
└── main.py                       # Application entry point
```

## Phase 1: Foundation (Tasks 1-3)

### Task 1: Design Voice Journal Architecture ✓
**Status:** Complete
**Deliverables:**
- Architecture document (VOICE_JOURNAL_PLAN.md)
- System diagram
- Redis schema design
- Module breakdown

### Task 2: Set up Redis Integration
**Duration:** 2-3 hours
**Steps:**
1. Install Redis locally or use Redis Cloud
2. Install redis-py client
3. Create `redis_memory.py` with connection pooling
4. Implement basic CRUD operations
5. Design and test Redis schema
6. Add error handling and reconnection logic

**Key Code:**
```python
# redis_memory.py
import redis
from redis import ConnectionPool

class RedisMemory:
    def __init__(self, host, port, password=None):
        self.pool = ConnectionPool(
            host=host,
            port=port,
            password=password,
            max_connections=50,
            decode_responses=True
        )
        self.client = redis.Redis(connection_pool=self.pool)
    
    def create_entry(self, user_id, entry_data):
        # Store journal entry as JSON
        pass
    
    def get_entry(self, user_id, entry_id):
        # Retrieve entry
        pass
    
    def update_session_context(self, user_id, session_id, context):
        # Update working memory with TTL
        pass
```

**Testing:**
- Connection pooling works
- CRUD operations successful
- TTL expiration works correctly
- Key naming follows conventions

### Task 3: Build Core Voice Journal Module
**Duration:** 3-4 hours
**Steps:**
1. Enhance `voice_recorder.py` from test script
2. Create `sarvam_client.py` wrapper
3. Build `journal_engine.py` orchestration
4. Implement entry creation flow
5. Add metadata extraction (timestamp, language, duration)

**Key Code:**
```python
# journal_engine.py
class JournalEngine:
    def __init__(self, redis_memory, sarvam_client, recorder):
        self.redis = redis_memory
        self.sarvam = sarvam_client
        self.recorder = recorder
    
    def create_entry(self, user_id, duration=30):
        # Record audio
        audio_file = self.recorder.record(duration)
        
        # Transcribe
        result = self.sarvam.transcribe(audio_file)
        
        # Create entry object
        entry = {
            "entry_id": generate_uuid(),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "transcript": result.transcript,
            "language_code": result.language_code,
            "audio_file_path": audio_file
        }
        
        # Store in Redis
        self.redis.create_entry(user_id, entry)
        
        return entry
```

## Phase 2: Working Memory (Task 4)

### Task 4: Implement Working Memory System
**Duration:** 2-3 hours
**Steps:**
1. Design session management with TTL
2. Implement conversation context tracking
3. Store recent N entries in working memory
4. Build context retrieval for AI responses
5. Add session cleanup on expiration

**Redis Operations:**
```python
# Session context with TTL
def update_session(self, user_id, session_id, context):
    key = f"session:context:{user_id}:{session_id}"
    self.client.hset(key, mapping=context)
    self.client.expire(key, 1800)  # 30 minutes

# Recent entries in working memory
def get_recent_entries(self, user_id, limit=10):
    timeline_key = f"journal:timeline:{user_id}"
    entry_ids = self.client.zrevrange(timeline_key, 0, limit-1)
    return [self.get_entry(user_id, eid) for eid in entry_ids]
```

## Phase 3: Semantic Search (Task 5)

### Task 5: Add Semantic Search with Vector Embeddings
**Duration:** 4-5 hours
**Steps:**
1. Install sentence-transformers or use OpenAI embeddings
2. Create `vector_search.py` module
3. Generate embeddings for journal entries
4. Create Redis vector index using RedisVL
5. Implement semantic search queries
6. Add hybrid search (vector + filters)

**Key Code:**
```python
# vector_search.py
from sentence_transformers import SentenceTransformer
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery

class VectorSearch:
    def __init__(self, redis_client):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = self.create_index()
    
    def generate_embedding(self, text):
        return self.model.encode(text).tolist()
    
    def search_similar(self, query_text, user_id, limit=5):
        query_vector = self.generate_embedding(query_text)
        
        results = self.index.search(VectorQuery(
            vector=query_vector,
            vector_field_name="embedding",
            return_fields=["entry_id", "transcript", "timestamp"],
            num_results=limit,
            filter_expression=f"@user_id:{{{user_id}}}"
        ))
        
        return results
```

## Phase 4: User Interface (Tasks 6-7)

### Task 6: Build Conversation Interface
**Duration:** 3-4 hours
**Commands:**
- `new` - Create new journal entry
- `search <query>` - Semantic search
- `review [date]` - Review entries by date
- `stats` - Show statistics
- `exit` - Exit application

### Task 7: Add Journal Entry Management
**Duration:** 2-3 hours
**Operations:**
- Create with metadata
- Read/search entries
- Update/edit entries
- Delete entries
- Tag management

## Phase 5: Advanced Features (Tasks 8-9)

### Task 8: Implement Multi-language Support
**Duration:** 2-3 hours
- Auto-detect language per entry
- Store language metadata
- Support code-mixed entries
- Translation mode

### Task 9: Add Analytics and Insights
**Duration:** 3-4 hours
- Entry frequency tracking
- Language usage patterns
- Topic clustering
- Export functionality

## Phase 6: Polish (Task 10)

### Task 10: Testing and Documentation
**Duration:** 3-4 hours
- Unit tests for all modules
- Integration tests
- User documentation
- API documentation
- Error handling
- Logging

## Total Estimated Time: 25-35 hours

## Dependencies to Install

```txt
sarvamai>=0.1.0
pyaudio>=0.2.13
redis>=5.0.0
redisvl>=0.1.0
sentence-transformers>=2.2.0
python-dotenv>=1.0.0
```

## Environment Variables

```bash
SARVAM_API_KEY=sk_0kh9urbr_zlWYVksa7nTw98jGnGT3LOuZ
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

