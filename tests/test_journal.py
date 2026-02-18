"""Tests for Voice Journal components."""
import asyncio
import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAudioHandler:
    """Tests for AudioHandler class."""
    
    def test_init(self):
        """Test AudioHandler initialization."""
        from src.audio_handler import AudioHandler
        handler = AudioHandler()
        assert handler.api_key is not None
        assert handler.RATE == 16000
        assert handler.CHANNELS == 1
    
    def test_recordings_dir_created(self):
        """Test that recordings directory is created."""
        from src.audio_handler import AudioHandler
        handler = AudioHandler()
        assert os.path.exists(handler.recordings_dir)


class TestMemoryClient:
    """Tests for MemoryClient class."""
    
    def test_init(self):
        """Test MemoryClient initialization."""
        from src.memory_client import MemoryClient
        client = MemoryClient()
        assert client.namespace == "voice-journal"
        assert "localhost" in client.base_url or "8001" in client.base_url
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        from src.memory_client import MemoryClient
        client = MemoryClient()
        # May fail if server not running, but shouldn't raise
        result = await client.health_check()
        assert isinstance(result, bool)
        await client.close()


class TestAudioStorage:
    """Tests for AudioStorage class."""
    
    def test_init(self):
        """Test AudioStorage initialization."""
        from src.audio_storage import AudioStorage
        storage = AudioStorage()
        assert storage.prefix == "voice_journal:audio"
    
    def test_key_generation(self):
        """Test Redis key generation."""
        from src.audio_storage import AudioStorage
        storage = AudioStorage()
        key = storage._key("test", "user1")
        assert key == "voice_journal:audio:test:user1"
    
    def test_store_and_get_metadata(self):
        """Test storing and retrieving audio metadata."""
        from src.audio_storage import AudioStorage
        storage = AudioStorage()
        
        entry_id = f"test_entry_{datetime.now().timestamp()}"
        user_id = "test_user"
        
        metadata = storage.store_audio_metadata(
            entry_id=entry_id,
            user_id=user_id,
            audio_file="/tmp/test.wav",
            transcript="Test transcript",
            language_code="en-IN",
            duration_seconds=5.0
        )
        
        assert metadata["entry_id"] == entry_id
        assert metadata["user_id"] == user_id
        
        # Retrieve
        retrieved = storage.get_audio_metadata(entry_id)
        assert retrieved is not None
        assert retrieved["transcript"] == "Test transcript"
        
        # Cleanup
        storage.delete_entry(entry_id, user_id)


class TestJournalManager:
    """Tests for JournalManager class."""
    
    def test_init(self):
        """Test JournalManager initialization."""
        from src.journal_manager import JournalManager
        manager = JournalManager()
        assert manager.prefix == "voice_journal:entries"
    
    def test_create_and_get_entry(self):
        """Test creating and retrieving an entry."""
        from src.journal_manager import JournalManager
        manager = JournalManager()
        
        entry = manager.create_entry(
            user_id="test_user",
            transcript="Test journal entry",
            language_code="en-IN",
            mood="happy",
            tags=["test", "demo"]
        )
        
        assert entry["transcript"] == "Test journal entry"
        assert entry["mood"] == "happy"
        assert "entry_id" in entry
        
        # Retrieve
        retrieved = manager.get_entry(entry["entry_id"])
        assert retrieved is not None
        assert retrieved["transcript"] == "Test journal entry"
        
        # Cleanup
        manager.delete_entry(entry["entry_id"])
    
    def test_update_entry(self):
        """Test updating an entry."""
        from src.journal_manager import JournalManager
        manager = JournalManager()
        
        entry = manager.create_entry(
            user_id="test_user",
            transcript="Original text",
            language_code="en-IN"
        )
        
        updated = manager.update_entry(
            entry["entry_id"],
            transcript="Updated text",
            mood="excited"
        )
        
        assert updated["transcript"] == "Updated text"
        assert updated["mood"] == "excited"
        
        # Cleanup
        manager.delete_entry(entry["entry_id"])


class TestLanguageSupport:
    """Tests for LanguageSupport class."""
    
    def test_supported_languages(self):
        """Test supported languages."""
        from src.language_support import LanguageSupport
        lang = LanguageSupport()
        assert len(lang.SUPPORTED_LANGUAGES) >= 20
        assert "en-IN" in lang.SUPPORTED_LANGUAGES
        assert "hi-IN" in lang.SUPPORTED_LANGUAGES
    
    def test_get_language_name(self):
        """Test getting language name."""
        from src.language_support import LanguageSupport
        lang = LanguageSupport()
        assert lang.get_language_name("en-IN") == "English (India)"
        assert lang.get_language_name("hi-IN") == "Hindi"


class TestAnalytics:
    """Tests for JournalAnalytics class."""
    
    def test_init(self):
        """Test JournalAnalytics initialization."""
        from src.analytics import JournalAnalytics
        analytics = JournalAnalytics()
        assert analytics.entries_prefix == "voice_journal:entries"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

