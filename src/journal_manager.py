"""Journal entry management with CRUD operations."""
import os
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import redis
from dotenv import load_dotenv

load_dotenv()


class JournalManager:
    """Manage journal entries with CRUD operations."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.client = redis.from_url(self.redis_url)
        self.prefix = "voice_journal:entries"
    
    def _key(self, *parts: str) -> str:
        """Build a Redis key."""
        return ":".join([self.prefix, *parts])
    
    def create_entry(
        self,
        user_id: str,
        transcript: str,
        language_code: str,
        audio_file: Optional[str] = None,
        mood: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new journal entry.
        
        Args:
            user_id: User identifier
            transcript: Entry text content
            language_code: Language of the entry
            audio_file: Optional path to audio file
            mood: Optional mood tag (happy, sad, neutral, etc.)
            tags: Optional list of tags
            metadata: Additional metadata
            
        Returns:
            Created entry dict with entry_id
        """
        entry_id = f"entry_{uuid.uuid4().hex}"
        now = datetime.now(timezone.utc)
        
        entry = {
            "entry_id": entry_id,
            "user_id": user_id,
            "transcript": transcript,
            "language_code": language_code,
            "audio_file": audio_file,
            "mood": mood,
            "tags": tags or [],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "timestamp": now.timestamp(),
            **(metadata or {})
        }
        
        # Store entry
        self.client.set(self._key(entry_id), json.dumps(entry))
        
        # Add to user's entry list
        self.client.zadd(self._key("user", user_id), {entry_id: now.timestamp()})
        
        # Index by mood if provided
        if mood:
            self.client.sadd(self._key("mood", user_id, mood), entry_id)
        
        # Index by tags
        for tag in (tags or []):
            self.client.sadd(self._key("tag", user_id, tag.lower()), entry_id)
        
        # Index by language
        self.client.sadd(self._key("lang", user_id, language_code), entry_id)
        
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entry by ID."""
        data = self.client.get(self._key(entry_id))
        return json.loads(data) if data else None
    
    def update_entry(
        self,
        entry_id: str,
        transcript: Optional[str] = None,
        mood: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an existing entry."""
        entry = self.get_entry(entry_id)
        if not entry:
            return None
        
        user_id = entry["user_id"]
        old_mood = entry.get("mood")
        old_tags = entry.get("tags", [])
        
        # Update fields
        if transcript is not None:
            entry["transcript"] = transcript
        if mood is not None:
            # Update mood index
            if old_mood:
                self.client.srem(self._key("mood", user_id, old_mood), entry_id)
            self.client.sadd(self._key("mood", user_id, mood), entry_id)
            entry["mood"] = mood
        if tags is not None:
            # Update tag indexes
            for tag in old_tags:
                self.client.srem(self._key("tag", user_id, tag.lower()), entry_id)
            for tag in tags:
                self.client.sadd(self._key("tag", user_id, tag.lower()), entry_id)
            entry["tags"] = tags
        if metadata:
            entry.update(metadata)
        
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # Save updated entry
        self.client.set(self._key(entry_id), json.dumps(entry))
        return entry
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        entry = self.get_entry(entry_id)
        if not entry:
            return False
        
        user_id = entry["user_id"]
        
        # Remove from indexes
        self.client.zrem(self._key("user", user_id), entry_id)
        
        if entry.get("mood"):
            self.client.srem(self._key("mood", user_id, entry["mood"]), entry_id)
        
        for tag in entry.get("tags", []):
            self.client.srem(self._key("tag", user_id, tag.lower()), entry_id)
        
        self.client.srem(self._key("lang", user_id, entry["language_code"]), entry_id)
        
        # Delete entry
        self.client.delete(self._key(entry_id))
        return True
    
    def list_entries(
        self,
        user_id: str,
        start: int = 0,
        count: int = 50,
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """List user entries with pagination."""
        if reverse:
            entry_ids = self.client.zrevrange(self._key("user", user_id), start, start + count - 1)
        else:
            entry_ids = self.client.zrange(self._key("user", user_id), start, start + count - 1)
        
        return [self.get_entry(eid.decode() if isinstance(eid, bytes) else eid) 
                for eid in entry_ids if eid]
    
    def search_by_mood(self, user_id: str, mood: str) -> List[Dict[str, Any]]:
        """Search entries by mood."""
        entry_ids = self.client.smembers(self._key("mood", user_id, mood))
        return [self.get_entry(eid.decode() if isinstance(eid, bytes) else eid) 
                for eid in entry_ids if eid]
    
    def search_by_tag(self, user_id: str, tag: str) -> List[Dict[str, Any]]:
        """Search entries by tag."""
        entry_ids = self.client.smembers(self._key("tag", user_id, tag.lower()))
        return [self.get_entry(eid.decode() if isinstance(eid, bytes) else eid) 
                for eid in entry_ids if eid]

