"""Audio metadata storage using Redis."""
import os
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import redis
from dotenv import load_dotenv

load_dotenv()


class AudioStorage:
    """Store and retrieve audio file metadata using Redis."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self.client = redis.from_url(self.redis_url)
        self.prefix = "voice_journal:audio"
    
    def _key(self, *parts: str) -> str:
        """Build a Redis key."""
        return ":".join([self.prefix, *parts])
    
    def store_audio_metadata(
        self,
        entry_id: str,
        user_id: str,
        audio_file: str,
        transcript: str,
        language_code: str,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store audio file metadata.
        
        Args:
            entry_id: Unique entry identifier
            user_id: User identifier
            audio_file: Path to audio file
            transcript: Transcribed text
            language_code: Detected language
            duration_seconds: Audio duration
            metadata: Additional metadata
            
        Returns:
            Stored metadata dict
        """
        now = datetime.now(timezone.utc)
        
        audio_metadata = {
            "entry_id": entry_id,
            "user_id": user_id,
            "audio_file": audio_file,
            "transcript": transcript,
            "language_code": language_code,
            "duration_seconds": duration_seconds,
            "created_at": now.isoformat(),
            "timestamp": now.timestamp(),
            **(metadata or {})
        }
        
        # Store metadata
        key = self._key("metadata", entry_id)
        self.client.set(key, json.dumps(audio_metadata))
        
        # Add to user's timeline (sorted by timestamp)
        timeline_key = self._key("timeline", user_id)
        self.client.zadd(timeline_key, {entry_id: now.timestamp()})
        
        # Add to date index
        date_key = self._key("date", user_id, now.strftime("%Y-%m-%d"))
        self.client.sadd(date_key, entry_id)
        
        # Add to language index
        lang_key = self._key("language", user_id, language_code)
        self.client.sadd(lang_key, entry_id)
        
        return audio_metadata
    
    def get_audio_metadata(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific entry."""
        key = self._key("metadata", entry_id)
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def get_user_timeline(
        self,
        user_id: str,
        start: int = 0,
        count: int = 50,
        reverse: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get user's audio entries in chronological order.
        
        Args:
            user_id: User identifier
            start: Start index
            count: Number of entries to return
            reverse: If True, newest first
            
        Returns:
            List of audio metadata dicts
        """
        timeline_key = self._key("timeline", user_id)
        
        if reverse:
            entry_ids = self.client.zrevrange(timeline_key, start, start + count - 1)
        else:
            entry_ids = self.client.zrange(timeline_key, start, start + count - 1)
        
        entries = []
        for entry_id in entry_ids:
            if isinstance(entry_id, bytes):
                entry_id = entry_id.decode()
            metadata = self.get_audio_metadata(entry_id)
            if metadata:
                entries.append(metadata)
        
        return entries
    
    def get_entries_by_date(
        self,
        user_id: str,
        date: str  # YYYY-MM-DD format
    ) -> List[Dict[str, Any]]:
        """Get all entries for a specific date."""
        date_key = self._key("date", user_id, date)
        entry_ids = self.client.smembers(date_key)
        
        entries = []
        for entry_id in entry_ids:
            if isinstance(entry_id, bytes):
                entry_id = entry_id.decode()
            metadata = self.get_audio_metadata(entry_id)
            if metadata:
                entries.append(metadata)
        
        return sorted(entries, key=lambda x: x.get("timestamp", 0))
    
    def get_entries_by_language(
        self,
        user_id: str,
        language_code: str
    ) -> List[Dict[str, Any]]:
        """Get all entries for a specific language."""
        lang_key = self._key("language", user_id, language_code)
        entry_ids = self.client.smembers(lang_key)
        
        entries = []
        for entry_id in entry_ids:
            if isinstance(entry_id, bytes):
                entry_id = entry_id.decode()
            metadata = self.get_audio_metadata(entry_id)
            if metadata:
                entries.append(metadata)
        
        return sorted(entries, key=lambda x: x.get("timestamp", 0), reverse=True)
    
    def delete_entry(self, entry_id: str, user_id: str):
        """Delete an audio entry and its indexes."""
        metadata = self.get_audio_metadata(entry_id)
        if not metadata:
            return
        
        # Remove from indexes
        timeline_key = self._key("timeline", user_id)
        self.client.zrem(timeline_key, entry_id)
        
        created_at = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
        date_key = self._key("date", user_id, created_at.strftime("%Y-%m-%d"))
        self.client.srem(date_key, entry_id)
        
        lang_key = self._key("language", user_id, metadata["language_code"])
        self.client.srem(lang_key, entry_id)
        
        # Delete metadata
        self.client.delete(self._key("metadata", entry_id))
    
    def get_entry_count(self, user_id: str) -> int:
        """Get total entry count for a user."""
        timeline_key = self._key("timeline", user_id)
        return self.client.zcard(timeline_key)

