"""Memory client wrapper for Redis Agent Memory Server."""
import os
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from dotenv import load_dotenv
import httpx
import redis
from agent_memory_client import create_memory_client
from agent_memory_client.models import MemoryMessage, ClientMemoryRecord, MemoryTypeEnum

load_dotenv()


class MemoryClient:
    """Wrapper for Redis Agent Memory Server operations."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        namespace: str = "voice-journal"
    ):
        self.base_url = base_url or os.getenv("MEMORY_SERVER_URL", "http://localhost:8001")
        self.namespace = namespace
        self._client = None
    
    async def _get_client(self):
        """Get or create the memory client."""
        if self._client is None:
            self._client = await create_memory_client(
                base_url=self.base_url,
                default_namespace=self.namespace
            )
        return self._client
    
    async def close(self):
        """Close the client connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def health_check(self) -> bool:
        """Check if the memory server is healthy."""
        try:
            async with httpx.AsyncClient() as http:
                response = await http.get(f"{self.base_url}/v1/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def add_journal_entry(
        self,
        session_id: str,
        user_id: str,
        transcript: str,
        language_code: str,
        audio_file: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a journal entry to working memory.
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            transcript: Transcribed text from audio
            language_code: Detected language code
            audio_file: Optional path to audio file
            metadata: Optional additional metadata
            
        Returns:
            Entry information dict
        """
        client = await self._get_client()
        now = datetime.now(timezone.utc)
        
        # Build entry content with metadata
        entry_metadata = {
            "type": "journal_entry",
            "language_code": language_code,
            "timestamp": now.isoformat(),
            "audio_file": audio_file,
            **(metadata or {})
        }
        
        # Create message
        message = MemoryMessage(
            role="user",
            content=transcript,
            created_at=now
        )
        
        # Get or create working memory and append
        created, _ = await client.get_or_create_working_memory(
            session_id=session_id,
            user_id=user_id
        )
        
        await client.append_messages_to_working_memory(
            session_id=session_id,
            messages=[message],
            user_id=user_id
        )
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "transcript": transcript,
            "language_code": language_code,
            "timestamp": now.isoformat(),
            "audio_file": audio_file,
            "new_session": created
        }

    async def create_journal_memory(
        self,
        user_id: str,
        transcript: str,
        language_code: str,
        topics: Optional[List[str]] = None,
        entities: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a journal entry directly in long-term memory.

        This stores the entry in the memory_idx index so it can be
        retrieved by search_long_term_memory.

        Args:
            user_id: User identifier
            transcript: The journal entry text
            language_code: Language code of the entry
            topics: Optional list of topics
            entities: Optional list of entities mentioned
            session_id: Optional session identifier

        Returns:
            Dict with status and memory info
        """
        client = await self._get_client()
        now = datetime.now(timezone.utc)

        # Create a memory record for long-term storage
        memory = ClientMemoryRecord(
            text=transcript,
            memory_type=MemoryTypeEnum.EPISODIC,  # Journal entries are episodic memories
            user_id=user_id,
            session_id=session_id,
            namespace=self.namespace,
            topics=topics or ["journal", "voice_entry"],
            entities=entities,
            created_at=now
        )

        try:
            response = await client.create_long_term_memory(
                memories=[memory],
                deduplicate=True
            )

            return {
                "status": response.status,
                "memory_id": memory.id,
                "user_id": user_id,
                "transcript": transcript,
                "timestamp": now.isoformat(),
                "stored_in_long_term": True
            }
        except Exception as e:
            print(f"Error creating long-term memory: {e}")
            return {
                "status": "error",
                "error": str(e),
                "stored_in_long_term": False
            }

    async def add_assistant_response(
        self,
        session_id: str,
        user_id: str,
        response: str
    ):
        """Add an assistant response to working memory."""
        client = await self._get_client()
        now = datetime.now(timezone.utc)
        
        message = MemoryMessage(
            role="assistant",
            content=response,
            created_at=now
        )
        
        await client.append_messages_to_working_memory(
            session_id=session_id,
            messages=[message],
            user_id=user_id
        )
    
    async def get_session_history(
        self,
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all messages from a session."""
        client = await self._get_client()
        
        _, working_memory = await client.get_or_create_working_memory(
            session_id=session_id,
            user_id=user_id
        )
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in working_memory.messages
        ]
    
    async def end_session(self, session_id: str):
        """End and cleanup a session."""
        client = await self._get_client()
        await client.delete_working_memory(session_id)

    async def search_long_term_memory(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        distance_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Search long-term memories using semantic search.

        This searches the memory_idx index on Redis Cloud.

        Args:
            query: The search query text
            user_id: Optional user ID to filter by
            limit: Maximum number of results
            distance_threshold: Maximum distance for results (0-1, lower is more similar)

        Returns:
            List of memory records with text, distance, and metadata
        """
        client = await self._get_client()

        try:
            # Import filter classes
            from agent_memory_client.filters import UserId

            # Build user_id filter if provided
            user_filter = UserId(eq=user_id) if user_id else None

            results = await client.search_long_term_memory(
                text=query,
                user_id=user_filter,
                limit=limit,
                distance_threshold=distance_threshold
            )

            # Convert to list of dicts
            memories = []
            for memory in results.memories:
                memories.append({
                    "id": memory.id,
                    "text": memory.text,
                    "distance": memory.dist,
                    "memory_type": memory.memory_type.value if memory.memory_type else None,
                    "topics": memory.topics,
                    "entities": memory.entities,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "user_id": memory.user_id,
                    "namespace": memory.namespace
                })

            return memories

        except Exception as e:
            print(f"Error searching long-term memory: {e}")
            return []

    async def search_memory_tool(
        self,
        query: str,
        user_id: Optional[str] = None,
        topics: Optional[List[str]] = None,
        max_results: int = 10,
        min_relevance: float = 0.3
    ) -> Dict[str, Any]:
        """
        Simplified memory search designed for LLM tool use.

        Args:
            query: The search query
            user_id: Optional user ID filter
            topics: Optional list of topics to filter by
            max_results: Maximum results to return
            min_relevance: Minimum relevance score (0-1)

        Returns:
            Dict with 'summary', 'memories' list, and 'total'
        """
        client = await self._get_client()

        try:
            result = await client.search_memory_tool(
                query=query,
                user_id=user_id,
                topics=topics,
                max_results=max_results,
                min_relevance=min_relevance
            )
            return result
        except Exception as e:
            print(f"Error in search_memory_tool: {e}")
            return {
                "summary": f"Search failed: {e}",
                "memories": [],
                "total": 0
            }

