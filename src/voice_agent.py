"""Voice Journal Agent - Main conversational agent.

Handles:
- Mode switching (Log mode vs Chat mode)
- Context assembly from retrieved entries
- Natural voice-first response generation
- Delete confirmation flow
"""
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import httpx
from dotenv import load_dotenv

from src.journal_store import JournalStore, JournalEntry
from src.intent_detector import IntentDetector, Intent, IntentResult
from src.memory_client import MemoryClient

load_dotenv()


class AgentMode(Enum):
    LOG = "log"      # User is logging entries
    CHAT = "chat"    # User is querying/chatting about entries


@dataclass
class AgentState:
    """Tracks agent conversation state."""
    mode: AgentMode = AgentMode.LOG
    pending_delete: Optional[Dict[str, Any]] = None  # Tracks pending delete confirmation
    last_entries_shown: List[str] = field(default_factory=list)  # Entry IDs shown in last response
    conversation_history: List[Dict[str, str]] = field(default_factory=list)


class VoiceJournalAgent:
    """Main voice journal agent."""
    
    # Response constraints
    MAX_RESPONSE_WORDS = 80  # ~12 seconds of speech
    MAX_CONTEXT_ENTRIES = 8
    
    HELP_RESPONSE = """I'm your voice journal assistant. Here's what I can do:
• Say "log my note" followed by your entry to record thoughts
• Ask "what did I say about..." to search your entries
• Say "summarize my week" for a recap
• Say "delete" to remove entries
• Ask me anything about your past notes!"""

    def __init__(self, user_id: str = "default_user", memory_client: Optional[MemoryClient] = None):
        self.user_id = user_id
        self.store = JournalStore()
        self.memory_client = memory_client  # For searching long-term memory (memory_idx)
        self.intent_detector = IntentDetector(use_llm=True)
        self.state = AgentState()
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    async def process_input(self, text: str) -> Tuple[str, Optional[bytes]]:
        """
        Process user input and generate response.
        
        Args:
            text: User's spoken/typed input
            
        Returns:
            Tuple of (response_text, optional_audio_bytes)
        """
        # Detect intent
        intent_result = await self.intent_detector.detect(text)
        
        # Handle based on intent
        response = await self._handle_intent(intent_result)
        
        # Add to conversation history
        self.state.conversation_history.append({"role": "user", "content": text})
        self.state.conversation_history.append({"role": "assistant", "content": response})
        
        # Keep history bounded
        if len(self.state.conversation_history) > 20:
            self.state.conversation_history = self.state.conversation_history[-20:]
        
        return response, None  # Audio generation handled separately
    
    async def _handle_intent(self, result: IntentResult) -> str:
        """Route to appropriate handler based on intent."""
        handlers = {
            Intent.LOG_ENTRY: self._handle_log,
            Intent.ASK_JOURNAL: self._handle_ask,
            Intent.SUMMARIZE: self._handle_summarize,
            Intent.DELETE_ENTRY: self._handle_delete_entry,
            Intent.DELETE_RANGE: self._handle_delete_range,
            Intent.DELETE_ALL: self._handle_delete_all,
            Intent.CONFIRM_DELETE: self._handle_confirm_delete,
            Intent.HELP: self._handle_help,
            Intent.UNKNOWN: self._handle_unknown,
        }
        
        handler = handlers.get(result.intent, self._handle_unknown)
        return await handler(result)
    
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
        """Handle questions about journal entries."""
        self.state.mode = AgentMode.CHAT
        query = result.entities.get("query", result.original_text)

        # Search for relevant entries using Agent Memory Server's long-term memory
        if not self.memory_client:
            return "Sorry, memory service is not available. Could you try again later?"

        try:
            memories = await self.memory_client.search_long_term_memory(
                query=query,
                user_id=self.user_id,
                limit=self.MAX_CONTEXT_ENTRIES,
                distance_threshold=0.8
            )
            print(f"[Memory Search] Found {len(memories)} memories for query: '{query}'")
        except Exception as e:
            print(f"[Memory Search] Error: {e}")
            return "Sorry, I had trouble searching your entries. Could you try again?"

        if not memories:
            return "I couldn't find any entries about that. Would you like to log something about it?"

        # Build context from memory search results
        context = self._build_memory_context(memories)
        response = await self._generate_chat_response(query, context)
        self.state.last_entries_shown = [m.get("id", "") for m in memories]
        return response

    async def _handle_summarize(self, result: IntentResult) -> str:
        """Handle summarization requests."""
        self.state.mode = AgentMode.CHAT

        # Get date range from entities
        entities = result.entities
        if entities.get("start") and entities.get("end"):
            start = datetime.fromisoformat(entities["start"])
            end = datetime.fromisoformat(entities["end"])
        else:
            # Default to last 7 days
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)

        entries = self.store.get_entries_by_date_range(self.user_id, start, end)

        if not entries:
            period = self._describe_period(start, end)
            return f"I don't have any entries from {period}. Would you like to log something now?"

        # Build summary
        context = self._build_context_pack([(e, 1.0) for e in entries])
        prompt = f"Summarize these journal entries in 2-3 sentences, focusing on key themes and feelings:\n\n{context}"
        summary = await self._call_llm(prompt, max_tokens=150)

        return f"{summary} Want more detail on any particular topic?"

    def _describe_period(self, start: datetime, end: datetime) -> str:
        """Describe a time period naturally."""
        days = (end - start).days
        if days <= 1:
            return "today"
        elif days <= 7:
            return "this week"
        elif days <= 30:
            return "this month"
        else:
            return f"the last {days} days"

    async def _handle_delete_entry(self, result: IntentResult) -> str:
        """Handle delete single entry request."""
        entry_id = result.entities.get("entry_id")

        if not entry_id and self.state.last_entries_shown:
            # Assume they want to delete the most recent one mentioned
            entry_id = self.state.last_entries_shown[0]

        if not entry_id:
            return "Which entry would you like to delete? You can ask me about your entries first."

        entry = self.store.get_entry(entry_id)
        if not entry:
            return "I couldn't find that entry. Would you like to see your recent entries?"

        # Store pending delete and ask for confirmation
        self.state.pending_delete = {"type": "entry", "entry_id": entry_id}
        preview = entry.transcript[:50] + "..." if len(entry.transcript) > 50 else entry.transcript
        return f"Delete this entry: \"{preview}\"? Say 'confirm delete' to proceed."

    async def _handle_delete_range(self, result: IntentResult) -> str:
        """Handle delete by date range request."""
        entities = result.entities
        if entities.get("start") and entities.get("end"):
            start = datetime.fromisoformat(entities["start"])
            end = datetime.fromisoformat(entities["end"])
        else:
            return "What time period would you like to delete? For example, 'delete entries from last week'."

        # Count entries in range
        entries = self.store.get_entries_by_date_range(self.user_id, start, end)
        count = len(entries)

        if count == 0:
            return f"There are no entries from {self._describe_period(start, end)} to delete."

        # Store pending delete
        self.state.pending_delete = {
            "type": "range",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "count": count
        }
        period = self._describe_period(start, end)
        return f"This will delete {count} entries from {period}. Are you sure? Say 'confirm delete' to proceed."

    async def _handle_delete_all(self, result: IntentResult) -> str:
        """Handle delete all entries request."""
        count = self.store.get_entry_count(self.user_id)

        if count == 0:
            return "You don't have any entries to delete."

        self.state.pending_delete = {"type": "all", "count": count}
        return f"This will permanently delete all {count} of your journal entries. Are you sure? Say 'confirm delete' to proceed."

    async def _handle_confirm_delete(self, result: IntentResult) -> str:
        """Handle delete confirmation."""
        if not self.state.pending_delete:
            return "There's nothing to confirm. What would you like to do?"

        delete_info = self.state.pending_delete
        self.state.pending_delete = None

        if delete_info["type"] == "entry":
            success = self.store.soft_delete(delete_info["entry_id"])
            return "Entry deleted." if success else "Sorry, couldn't delete that entry."

        elif delete_info["type"] == "range":
            start = datetime.fromisoformat(delete_info["start"])
            end = datetime.fromisoformat(delete_info["end"])
            count = self.store.delete_by_date_range(self.user_id, start, end)
            return f"Deleted {count} entries."

        elif delete_info["type"] == "all":
            count = self.store.delete_all(self.user_id)
            return f"All {count} entries have been deleted. Fresh start!"

        return "Something went wrong with the delete. Please try again."

    async def _handle_help(self, result: IntentResult) -> str:
        """Handle help request."""
        return self.HELP_RESPONSE

    async def _handle_unknown(self, result: IntentResult) -> str:
        """Handle unknown intent - default to asking or logging based on punctuation."""
        text = result.original_text

        # If it looks like a question, treat as ASK
        if "?" in text or text.lower().startswith(("what", "when", "how", "why", "did", "have", "do", "is", "are")):
            return await self._handle_ask(IntentResult(
                Intent.ASK_JOURNAL, 0.5, {"query": text}, text
            ))

        # Otherwise treat as a log entry
        return await self._handle_log(IntentResult(
            Intent.LOG_ENTRY, 0.5, {"content": text}, text
        ))

    def _build_context_pack(self, entries_with_scores: List[Tuple[JournalEntry, float]]) -> str:
        """
        Build a compact context pack from entries.

        Format: bullet list with date + summary + key quote if needed
        """
        lines = []
        for entry, score in entries_with_scores:
            # Parse timestamp
            ts = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
            date_str = ts.strftime("%b %d")

            # Use summary or truncated transcript
            summary = entry.summary or entry.transcript[:100]
            if len(summary) > 100:
                summary = summary[:100] + "..."

            # Format: "• Mar 15: Summary text"
            lines.append(f"• {date_str}: {summary}")

        return "\n".join(lines)

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

    async def _generate_chat_response(self, query: str, context: str) -> str:
        """Generate a natural response based on query and context."""
        system_prompt = """You are a helpful voice journal assistant. Your responses should be:
- Brief (under 80 words, suitable for ~12 seconds of speech)
- Natural and conversational
- Based ONLY on the provided journal entries - never invent content
- If the context doesn't have relevant info, say so honestly
- End with a short follow-up question only if it adds value

IMPORTANT: If you can't find information in the context, say "I don't have entries about that" rather than making things up."""

        user_prompt = f"""User's question: {query}

Their journal entries:
{context}

Answer based only on these entries. Be brief and natural."""

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

    def clear_pending_delete(self) -> None:
        """Clear any pending delete operation."""
        self.state.pending_delete = None

