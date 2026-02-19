"""Voice Journal Agent - Main conversational agent.

Handles:
- Mode switching (Log mode vs Chat mode)
- Context assembly from retrieved entries
- Natural voice-first response generation
"""
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import httpx
from dotenv import load_dotenv

from src.journal_store import JournalStore
from src.intent_detector import Intent, IntentResult  # Keep Intent/IntentResult, remove IntentDetector
from src.memory_client import MemoryClient
from src.calendar_client import CalendarClient
from src.intent_router import get_intent_router

load_dotenv()


class AgentMode(Enum):
    LOG = "log"      # User is logging entries
    CHAT = "chat"    # User is querying/chatting about entries


@dataclass
class AgentState:
    """Tracks agent conversation state."""
    mode: AgentMode = AgentMode.LOG
    last_entries_shown: List[str] = field(default_factory=list)
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


class VoiceJournalAgent:
    """Main voice journal agent."""

    def __init__(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        memory_client: Optional[MemoryClient] = None
    ):
        self.user_id = user_id
        self.session_id = session_id  # For working memory (conversation continuity)
        self.store = JournalStore()
        self.memory_client = memory_client  # For searching long-term memory (memory_idx)
        self.state = AgentState()
        self.api_key = os.getenv("OPENAI_API_KEY")

        # Initialize calendar client (lazy load on first use)
        self._calendar_client: Optional[CalendarClient] = None

        # Semantic router for intent detection (lazy load)
        self._intent_router = None

    # Fallback keywords (used if semantic router fails)
    LOG_KEYWORDS = ["log my note", "note this", "record this", "journal this", "save this", "remember this"]

    @property
    def calendar_client(self) -> Optional[CalendarClient]:
        """Lazy-load calendar client."""
        if self._calendar_client is None:
            try:
                self._calendar_client = CalendarClient()
            except Exception as e:
                print(f"[Calendar] Init error: {e}")
        return self._calendar_client

    async def process_input(self, text: str) -> Tuple[str, Optional[bytes]]:
        """
        Process user input and generate response.

        Uses semantic router for intent detection:
        - "log" intent -> save as journal entry
        - "calendar" intent -> fetch calendar + respond
        - "chat" intent -> search journal + respond
        """
        import time
        import asyncio

        # Use semantic router for intent detection
        intent_start = time.time()
        try:
            if self._intent_router is None:
                self._intent_router = get_intent_router()
            # Run in thread to avoid blocking (embedding API call)
            intent, confidence = await asyncio.to_thread(
                self._intent_router.detect, text, 0.5
            )
        except Exception as e:
            print(f"[Intent Router] Error: {e}, falling back to keywords")
            # Fallback to keyword matching
            text_lower = text.lower()
            if any(kw in text_lower for kw in self.LOG_KEYWORDS):
                intent, confidence = "log", 0.8
            else:
                intent, confidence = "chat", 0.5

        print(f"[TIMING] Intent detection: {time.time() - intent_start:.2f}s -> {intent} ({confidence:.2f})")

        if intent == "log":
            # Extract content (remove common prefixes)
            content = text
            for prefix in ["log my note", "note this down", "remember this", "record this", "note this"]:
                if text.lower().startswith(prefix):
                    content = text[len(prefix):].strip()
                    if content.startswith(":"):
                        content = content[1:].strip()
                    break
            if not content:
                content = text

            result = IntentResult(Intent.LOG_ENTRY, confidence, {"content": content}, text)
            response = await self._handle_log(result)
        else:
            # Both "calendar" and "chat" go through _handle_ask (it detects calendar internally)
            result = IntentResult(Intent.ASK_JOURNAL, confidence, {"query": text, "is_calendar": intent == "calendar"}, text)
            response = await self._handle_ask(result)

        # Add to conversation history
        self.state.conversation_history.append({"role": "user", "content": text})
        self.state.conversation_history.append({"role": "assistant", "content": response})

        # Keep history bounded
        if len(self.state.conversation_history) > 20:
            self.state.conversation_history = self.state.conversation_history[-20:]

        return response, None  # Audio generation handled separately

    async def _handle_log(self, result: IntentResult) -> str:
        """Handle logging a new entry."""
        self.state.mode = AgentMode.LOG
        content = result.entities.get("content", result.original_text)

        # Clean up log-specific phrases from transcript
        for phrase in ["log my note", "note this", "record this", "journal this"]:
            if content.lower().startswith(phrase):
                content = content[len(phrase):].strip()
                if content.startswith(":"): content = content[1:].strip()

        if not content or len(content) < 5:
            return "I didn't catch what you wanted to log. What would you like to note down?"

        # Store in long-term memory via memory_client
        try:
            if self.memory_client:
                await self.memory_client.create_journal_memory(
                    user_id=self.user_id,
                    transcript=content,
                    language_code="en-IN",
                    topics=["journal", "chat_entry"]
                )
                return "Got it! I've saved your note. Anything else?"
            else:
                return "Sorry, memory service is not available. Could you try again later?"
        except Exception as e:
            print(f"Error saving entry: {e}")
            return "Sorry, I had trouble saving that. Could you try again?"
    
    async def _handle_ask(self, result: IntentResult) -> str:
        """Handle questions about journal entries and calendar."""
        import time
        import asyncio
        self.state.mode = AgentMode.CHAT
        query = result.entities.get("query", result.original_text)

        # Search for relevant entries using Agent Memory Server's long-term memory
        if not self.memory_client:
            return "Sorry, memory service is not available. Could you try again later?"

        # Use intent from semantic router (passed via entities)
        is_calendar_query = result.entities.get("is_calendar", False)

        # Run fetches IN PARALLEL
        parallel_start = time.time()

        async def fetch_conversation():
            if self.session_id:
                try:
                    return await self.memory_client.get_conversation_context(
                        session_id=self.session_id,
                        user_id=self.user_id,
                        max_turns=3
                    )
                except Exception as e:
                    print(f"[Working Memory] Error: {e}")
            return ""

        async def search_memories():
            # Skip memory search for pure calendar queries (faster)
            if is_calendar_query:
                return []
            try:
                return await self.memory_client.search_long_term_memory(
                    query=query,
                    user_id=self.user_id,
                    limit=5,
                    distance_threshold=0.8
                )
            except Exception as e:
                print(f"[Memory Search] Error: {e}")
                return []

        async def fetch_calendar():
            if is_calendar_query and self.calendar_client:
                try:
                    # Run sync calendar API in thread pool to avoid blocking
                    return await asyncio.to_thread(self.calendar_client.get_calendar_context)
                except Exception as e:
                    print(f"[Calendar] Error: {e}")
            return ""

        # Execute in parallel
        conversation_context, memories, calendar_context = await asyncio.gather(
            fetch_conversation(),
            search_memories(),
            fetch_calendar()
        )
        print(f"[TIMING] Parallel fetch: {time.time() - parallel_start:.2f}s (memories: {len(memories)}, calendar: {bool(calendar_context)})")

        # Build context and generate response
        journal_context = self._build_memory_context(memories) if memories else ""

        llm_start = time.time()
        response = await self._generate_chat_response(query, journal_context, conversation_context, calendar_context)
        print(f"[TIMING] LLM response: {time.time() - llm_start:.2f}s")

        self.state.last_entries_shown = [m.get("id", "") for m in memories] if memories else []

        # Save conversation turn in background (fire and forget - don't block response)
        if self.session_id:
            asyncio.create_task(self._save_turn_background(query, response))

        return response

    async def _save_turn_background(self, user_message: str, assistant_response: str):
        """Save conversation turn in background without blocking."""
        try:
            await self.memory_client.save_conversation_turn(
                session_id=self.session_id,
                user_id=self.user_id,
                user_message=user_message,
                assistant_response=assistant_response
            )
        except Exception as e:
            print(f"[Working Memory] Background save error: {e}")

    def _build_memory_context(self, memories: List[Dict[str, Any]]) -> str:
        """
        Build a compact context pack from memory search results.

        Format: bullet list with date + text snippet
        """
        lines = []
        for memory in memories:
            # Extract date from created_at
            created_at = memory.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime("%b %d")
                except Exception:
                    date_str = "Recent"
            else:
                date_str = "Recent"

            # Get text content (limit length for voice-first response)
            text = memory.get("text", "")
            if len(text) > 150:
                text = text[:150] + "..."

            lines.append(f"• {date_str}: {text}")

        return "\n".join(lines)

    async def _generate_chat_response(
        self,
        query: str,
        journal_context: str,
        conversation_context: str = "",
        calendar_context: str = ""
    ) -> str:
        """Generate a natural response based on query, journal context, conversation history, and calendar."""
        system_prompt = """You are a voice journal assistant with calendar access. Be brief and natural.
- Max 2-3 sentences
- Use journal entries and calendar events as context
- For calendar queries, mention specific events and times
- Maintain conversation flow"""

        # Build compact prompt
        parts = []
        if conversation_context:
            parts.append(f"Chat history:\n{conversation_context}")
        if calendar_context:
            parts.append(f"Calendar:\n{calendar_context}")
        if journal_context:
            parts.append(f"Journal:\n{journal_context}")
        parts.append(f"User: {query}")

        user_prompt = "\n\n".join(parts)

        response = await self._call_llm(
            user_prompt,
            system=system_prompt,
            max_tokens=120
        )

        return response

    async def _call_llm(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        max_tokens: int = 150
    ) -> str:
        """Call OpenAI API for text generation."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7
                    },
                    timeout=15.0
                )
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"LLM call failed: {e}")
            return "I'm having trouble thinking right now. Could you try again?"

    def get_mode(self) -> str:
        """Get current agent mode."""
        return self.state.mode.value

    def set_mode(self, mode: str) -> None:
        """Set agent mode."""
        if mode == "log":
            self.state.mode = AgentMode.LOG
        elif mode == "chat":
            self.state.mode = AgentMode.CHAT

