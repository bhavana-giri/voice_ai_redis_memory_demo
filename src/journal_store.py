"""Redis-backed Journal Store with Vector Search.

Schema:
- journal:entry:{id} - Hash with entry data
- journal:user:{user_id}:timeline - Sorted set by timestamp
- journal:idx - RediSearch index for vector + text search
"""
import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict, field
import redis
from redis.commands.search.field import TextField, NumericField, TagField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
import numpy as np
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_DIM = 1536  # OpenAI ada-002 dimension
INDEX_NAME = "journal_idx"


@dataclass
class JournalEntry:
    """A single journal entry."""
    id: str
    user_id: str
    timestamp: str  # ISO format
    transcript: str
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    mood: str = ""
    language_code: str = "en-IN"
    deleted: bool = False
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for Redis storage."""
        d = asdict(self)
        d['tags'] = ','.join(self.tags) if self.tags else ''
        d['deleted'] = int(self.deleted)
        # Store embedding as bytes
        if self.embedding:
            d['embedding'] = np.array(self.embedding, dtype=np.float32).tobytes()
        else:
            d['embedding'] = b''
        return d
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'JournalEntry':
        """Create from Redis hash data."""
        # Handle bytes from Redis
        for k, v in d.items():
            if isinstance(v, bytes):
                d[k] = v.decode('utf-8') if k != 'embedding' else v
        
        tags = d.get('tags', '')
        d['tags'] = tags.split(',') if tags else []
        d['deleted'] = bool(int(d.get('deleted', 0)))
        
        # Convert embedding bytes back to list
        emb_bytes = d.get('embedding', b'')
        if emb_bytes and len(emb_bytes) > 0:
            d['embedding'] = np.frombuffer(emb_bytes, dtype=np.float32).tolist()
        else:
            d['embedding'] = None
        
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class JournalStore:
    """Redis-backed journal storage with vector search."""
    
    def __init__(self, redis_url: Optional[str] = None, embedding_client=None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.client = redis.from_url(self.redis_url, decode_responses=False)
        self.embedding_client = embedding_client
        self._ensure_index()
    
    def _ensure_index(self):
        """Create RediSearch index if it doesn't exist."""
        try:
            self.client.ft(INDEX_NAME).info()
        except redis.ResponseError:
            # Create the index
            schema = (
                TextField("$.transcript", as_name="transcript"),
                TextField("$.summary", as_name="summary"),
                TagField("$.tags", as_name="tags", separator=","),
                TagField("$.user_id", as_name="user_id"),
                TagField("$.mood", as_name="mood"),
                NumericField("$.timestamp_unix", as_name="timestamp_unix"),
                TagField("$.deleted", as_name="deleted"),
                VectorField(
                    "$.embedding",
                    "FLAT",
                    {
                        "TYPE": "FLOAT32",
                        "DIM": EMBEDDING_DIM,
                        "DISTANCE_METRIC": "COSINE"
                    },
                    as_name="embedding"
                )
            )
            
            definition = IndexDefinition(
                prefix=["journal:entry:"],
                index_type=IndexType.JSON
            )
            
            self.client.ft(INDEX_NAME).create_index(
                schema,
                definition=definition
            )
    
    def _entry_key(self, entry_id: str) -> str:
        return f"journal:entry:{entry_id}"
    
    def _timeline_key(self, user_id: str) -> str:
        return f"journal:user:{user_id}:timeline"
    
    def _generate_id(self, user_id: str, timestamp: str) -> str:
        """Generate unique entry ID."""
        content = f"{user_id}:{timestamp}:{uuid.uuid4().hex[:8]}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI."""
        if self.embedding_client:
            return await self.embedding_client.get_embedding(text)

        # Fallback to direct OpenAI call
        import httpx
        api_key = os.getenv("OPENAI_API_KEY")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "text-embedding-ada-002", "input": text},
                timeout=30.0
            )
            data = response.json()
            return data["data"][0]["embedding"]

    async def add_entry(
        self,
        user_id: str,
        transcript: str,
        summary: str = "",
        tags: List[str] = None,
        mood: str = "",
        language_code: str = "en-IN"
    ) -> JournalEntry:
        """Add a new journal entry with embedding."""
        timestamp = datetime.now(timezone.utc).isoformat()
        entry_id = self._generate_id(user_id, timestamp)

        # Generate embedding
        embedding = await self.get_embedding(transcript)

        entry = JournalEntry(
            id=entry_id,
            user_id=user_id,
            timestamp=timestamp,
            transcript=transcript,
            summary=summary or transcript[:200],
            tags=tags or [],
            mood=mood,
            language_code=language_code,
            embedding=embedding
        )

        # Store as JSON for RediSearch
        entry_data = {
            "id": entry.id,
            "user_id": entry.user_id,
            "timestamp": entry.timestamp,
            "timestamp_unix": datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00')).timestamp(),
            "transcript": entry.transcript,
            "summary": entry.summary,
            "tags": ','.join(entry.tags),
            "mood": entry.mood,
            "language_code": entry.language_code,
            "deleted": "false",
            "embedding": embedding
        }

        # Store entry
        self.client.json().set(self._entry_key(entry_id), "$", entry_data)

        # Add to timeline sorted set
        self.client.zadd(
            self._timeline_key(user_id),
            {entry_id: datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()}
        )

        return entry

    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a specific entry by ID."""
        data = self.client.json().get(self._entry_key(entry_id))
        if not data or data.get("deleted") == "true":
            return None

        # Convert back to JournalEntry
        data['tags'] = data.get('tags', '').split(',') if data.get('tags') else []
        data['deleted'] = data.get('deleted') == "true"
        return JournalEntry(**{k: v for k, v in data.items()
                               if k in JournalEntry.__dataclass_fields__ and k != 'timestamp_unix'})

    def soft_delete(self, entry_id: str) -> bool:
        """Soft delete an entry."""
        key = self._entry_key(entry_id)
        if self.client.exists(key):
            self.client.json().set(key, "$.deleted", "true")
            return True
        return False

    def delete_by_date_range(self, user_id: str, start: datetime, end: datetime) -> int:
        """Soft delete entries in date range."""
        start_ts = start.timestamp()
        end_ts = end.timestamp()

        entry_ids = self.client.zrangebyscore(
            self._timeline_key(user_id), start_ts, end_ts
        )

        count = 0
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            if self.soft_delete(eid):
                count += 1
        return count

    def delete_all(self, user_id: str) -> int:
        """Soft delete all entries for a user."""
        entry_ids = self.client.zrange(self._timeline_key(user_id), 0, -1)
        count = 0
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            if self.soft_delete(eid):
                count += 1
        return count

    async def search_similar(
        self,
        user_id: str,
        query: str,
        k: int = 5,
        recency_boost: float = 0.3
    ) -> List[Tuple[JournalEntry, float]]:
        """
        Search for similar entries using vector similarity + recency.

        Args:
            user_id: User to search for
            query: Search query text
            k: Number of results to return
            recency_boost: Weight for recency (0-1), rest goes to similarity

        Returns:
            List of (entry, combined_score) tuples
        """
        # Get query embedding
        query_embedding = await self.get_embedding(query)
        query_vector = np.array(query_embedding, dtype=np.float32).tobytes()

        # Build RediSearch query with vector similarity
        # Filter: user_id match AND not deleted
        search_query = (
            Query(f"(@user_id:{{{user_id}}}) (@deleted:{{false}})=>[KNN {k*2} @embedding $vec AS score]")
            .return_fields("id", "transcript", "summary", "tags", "mood", "timestamp", "language_code", "score")
            .sort_by("score")
            .dialect(2)
        )

        results = self.client.ft(INDEX_NAME).search(
            search_query,
            query_params={"vec": query_vector}
        )

        # Calculate combined scores with recency boost
        entries_with_scores = []
        now = datetime.now(timezone.utc).timestamp()
        max_age = 30 * 24 * 3600  # 30 days for normalization

        for doc in results.docs:
            entry_data = {
                "id": doc.id.split(":")[-1],
                "user_id": user_id,
                "transcript": doc.transcript,
                "summary": doc.summary,
                "tags": doc.tags.split(',') if doc.tags else [],
                "mood": doc.mood if hasattr(doc, 'mood') else "",
                "timestamp": doc.timestamp,
                "language_code": doc.language_code if hasattr(doc, 'language_code') else "en-IN",
                "deleted": False
            }
            entry = JournalEntry(**entry_data)

            # Vector similarity score (lower is better in COSINE, convert to higher=better)
            similarity = 1 - float(doc.score)

            # Recency score (newer = higher)
            entry_ts = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00')).timestamp()
            age = now - entry_ts
            recency = max(0, 1 - (age / max_age))

            # Combined score
            combined = (1 - recency_boost) * similarity + recency_boost * recency
            entries_with_scores.append((entry, combined))

        # Sort by combined score and return top k
        entries_with_scores.sort(key=lambda x: x[1], reverse=True)
        return entries_with_scores[:k]

    def get_recent_entries(self, user_id: str, limit: int = 10) -> List[JournalEntry]:
        """Get most recent entries for a user."""
        entry_ids = self.client.zrevrange(self._timeline_key(user_id), 0, limit - 1)

        entries = []
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            entry = self.get_entry(eid)
            if entry and not entry.deleted:
                entries.append(entry)
        return entries

    def get_entries_by_date_range(
        self,
        user_id: str,
        start: datetime,
        end: datetime
    ) -> List[JournalEntry]:
        """Get entries within a date range."""
        start_ts = start.timestamp()
        end_ts = end.timestamp()

        entry_ids = self.client.zrangebyscore(
            self._timeline_key(user_id), start_ts, end_ts
        )

        entries = []
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            entry = self.get_entry(eid)
            if entry and not entry.deleted:
                entries.append(entry)
        return entries

    def get_entry_count(self, user_id: str) -> int:
        """Get total non-deleted entry count for user."""
        entry_ids = self.client.zrange(self._timeline_key(user_id), 0, -1)
        count = 0
        for eid in entry_ids:
            if isinstance(eid, bytes):
                eid = eid.decode()
            entry = self.get_entry(eid)
            if entry and not entry.deleted:
                count += 1
        return count

