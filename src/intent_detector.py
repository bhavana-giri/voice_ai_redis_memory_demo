"""Intent detection for voice journal commands.

Supported intents:
- LOG_ENTRY: User is adding a note
- ASK_JOURNAL: Question about past notes
- SUMMARIZE: Time-based summary request
- DELETE_ENTRY: Delete specific entry
- DELETE_RANGE: Delete entries in date range
- DELETE_ALL: Delete all entries
- CONFIRM_DELETE: Confirmation for delete action
- HELP: Show capabilities
- UNKNOWN: Couldn't determine intent
"""
import os
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

load_dotenv()


class Intent(Enum):
    LOG_ENTRY = "log_entry"
    ASK_JOURNAL = "ask_journal"
    SUMMARIZE = "summarize"
    DELETE_ENTRY = "delete_entry"
    DELETE_RANGE = "delete_range"
    DELETE_ALL = "delete_all"
    CONFIRM_DELETE = "confirm_delete"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: Intent
    confidence: float
    entities: Dict[str, Any]
    original_text: str
    
    def __repr__(self):
        return f"IntentResult(intent={self.intent.value}, confidence={self.confidence:.2f})"


# Regex patterns for rule-based detection
LOG_PATTERNS = [
    r"^(log|record|add|save|note|journal|write down|remember)\b",
    r"^(today|this morning|tonight|right now)\b.*\bi\b",
    r"^i (want to|need to|'d like to) (log|record|note|journal)",
    r"^(here's|here is) (my|a) (note|entry|journal)",
]

ASK_PATTERNS = [
    r"what did i (say|mention|write|record|note) about",
    r"when did i (last )?(talk|mention|say|write) about",
    r"have i (ever )?(mentioned|said|written|talked) about",
    r"find (entries|notes|recordings) (about|with|containing)",
    r"search (for|my) (entries|notes|journal)",
    r"do i have any (notes|entries) (about|on|regarding)",
    # Question words - general questions are ASK_JOURNAL
    r"^(what|when|where|who|how|why|which|did|do|does|is|are|was|were|has|have|can|could|will|would)\b.*\??\s*$",
    r"^tell me (about|what|when|where)",
    r"^(show|give) me",
]

SUMMARIZE_PATTERNS = [
    r"summarize (my|the)? ?(last|past|this|yesterday)",
    r"(give me|show me|what's) (a )?summary",
    r"how (have i been|was i|am i) (doing|feeling)",
    r"what('ve| have) i (been|talked about|recorded)",
    r"recap (of )?(my|the|this|last)",
    r"overview of (my|the) (week|month|day|entries)",
]

DELETE_PATTERNS = [
    r"delete (the |my )?(entry|note|recording)",
    r"remove (the |my )?(entry|note|recording)",
    r"erase (the |my )?(entry|note|recording)",
]

DELETE_RANGE_PATTERNS = [
    r"delete (entries|notes|recordings) from",
    r"delete (everything|all) from (last|this|yesterday)",
    r"clear (entries|notes) (from|between)",
]

DELETE_ALL_PATTERNS = [
    r"delete (all|everything|all my)",
    r"clear (all|my entire|everything)",
    r"erase (all|everything|my entire)",
    r"wipe (all|everything|my)",
]

CONFIRM_PATTERNS = [
    r"^(yes,? )?confirm delete",
    r"^yes,? (delete|remove|erase)",
    r"^(i )?confirm",
]

HELP_PATTERNS = [
    r"^help$",
    r"what can you do",
    r"how (do i|can i|does this) (use|work)",
    r"show (me )?(commands|capabilities|features)",
]


class IntentDetector:
    """Detect user intent from text."""

    def __init__(self, use_llm: bool = False):  # Disabled LLM by default for speed
        self.use_llm = use_llm
        self.api_key = os.getenv("OPENAI_API_KEY")
    
    def _check_patterns(self, text: str, patterns: List[str]) -> bool:
        """Check if text matches any pattern."""
        text_lower = text.lower().strip()
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def _rule_based_detect(self, text: str) -> Optional[IntentResult]:
        """Try rule-based detection first."""
        text_lower = text.lower().strip()
        
        # Check confirm first (highest priority)
        if self._check_patterns(text, CONFIRM_PATTERNS):
            return IntentResult(Intent.CONFIRM_DELETE, 0.95, {}, text)
        
        # Check help
        if self._check_patterns(text, HELP_PATTERNS):
            return IntentResult(Intent.HELP, 0.95, {}, text)
        
        # Check delete patterns (order matters)
        if self._check_patterns(text, DELETE_ALL_PATTERNS):
            return IntentResult(Intent.DELETE_ALL, 0.85, {}, text)
        if self._check_patterns(text, DELETE_RANGE_PATTERNS):
            return IntentResult(Intent.DELETE_RANGE, 0.85, self._extract_date_range(text), text)
        if self._check_patterns(text, DELETE_PATTERNS):
            return IntentResult(Intent.DELETE_ENTRY, 0.85, self._extract_entry_id(text), text)
        
        # Check summarize
        if self._check_patterns(text, SUMMARIZE_PATTERNS):
            return IntentResult(Intent.SUMMARIZE, 0.85, self._extract_time_range(text), text)
        
        # Check ask
        if self._check_patterns(text, ASK_PATTERNS):
            return IntentResult(Intent.ASK_JOURNAL, 0.85, {"query": text}, text)
        
        # Check log
        if self._check_patterns(text, LOG_PATTERNS):
            return IntentResult(Intent.LOG_ENTRY, 0.85, {"content": text}, text)

        return None

    def _extract_date_range(self, text: str) -> Dict[str, Any]:
        """Extract date range from text."""
        now = datetime.now()
        text_lower = text.lower()

        if "today" in text_lower:
            start = now.replace(hour=0, minute=0, second=0)
            end = now
        elif "yesterday" in text_lower:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            end = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59)
        elif "last week" in text_lower or "this week" in text_lower:
            start = now - timedelta(days=7)
            end = now
        elif "last month" in text_lower or "this month" in text_lower:
            start = now - timedelta(days=30)
            end = now
        else:
            start = now - timedelta(days=7)
            end = now

        return {"start": start.isoformat(), "end": end.isoformat()}

    def _extract_time_range(self, text: str) -> Dict[str, Any]:
        """Extract time range for summarization."""
        return self._extract_date_range(text)

    def _extract_entry_id(self, text: str) -> Dict[str, Any]:
        """Extract entry ID if mentioned."""
        # Look for patterns like "entry 123" or "note #abc"
        match = re.search(r'(entry|note|recording)\s*#?\s*([a-z0-9]+)', text.lower())
        if match:
            return {"entry_id": match.group(2)}
        return {}

    async def detect(self, text: str) -> IntentResult:
        """Detect intent from text."""
        # Try rule-based first
        result = self._rule_based_detect(text)
        if result:
            return result

        # Fall back to LLM if enabled
        if self.use_llm:
            return await self._llm_detect(text)

        # Default to LOG_ENTRY for general statements, ASK_JOURNAL for questions
        if "?" in text or text.lower().startswith(("what", "when", "how", "why", "where", "who", "did", "have", "do")):
            return IntentResult(Intent.ASK_JOURNAL, 0.5, {"query": text}, text)

        return IntentResult(Intent.LOG_ENTRY, 0.5, {"content": text}, text)

    async def _llm_detect(self, text: str) -> IntentResult:
        """Use LLM for intent classification."""
        prompt = f"""Classify the user's intent for a voice journal app.

User message: "{text}"

Intents:
- LOG_ENTRY: User wants to add a new journal note
- ASK_JOURNAL: User is asking a question about their past journal entries
- SUMMARIZE: User wants a summary of entries (e.g., "summarize my week")
- DELETE_ENTRY: User wants to delete a specific entry
- DELETE_RANGE: User wants to delete entries in a date range
- DELETE_ALL: User wants to delete all entries
- HELP: User is asking for help or capabilities

Respond with ONLY the intent name (e.g., "LOG_ENTRY") and nothing else."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 20,
                        "temperature": 0
                    },
                    timeout=10.0
                )
                data = response.json()
                intent_str = data["choices"][0]["message"]["content"].strip().upper()

                # Map to enum
                intent_map = {
                    "LOG_ENTRY": Intent.LOG_ENTRY,
                    "ASK_JOURNAL": Intent.ASK_JOURNAL,
                    "SUMMARIZE": Intent.SUMMARIZE,
                    "DELETE_ENTRY": Intent.DELETE_ENTRY,
                    "DELETE_RANGE": Intent.DELETE_RANGE,
                    "DELETE_ALL": Intent.DELETE_ALL,
                    "HELP": Intent.HELP,
                }

                intent = intent_map.get(intent_str, Intent.UNKNOWN)

                # Extract entities based on intent
                entities = {}
                if intent == Intent.SUMMARIZE:
                    entities = self._extract_time_range(text)
                elif intent == Intent.ASK_JOURNAL:
                    entities = {"query": text}
                elif intent == Intent.LOG_ENTRY:
                    entities = {"content": text}
                elif intent in (Intent.DELETE_RANGE,):
                    entities = self._extract_date_range(text)

                return IntentResult(intent, 0.8, entities, text)

        except Exception as e:
            print(f"LLM intent detection failed: {e}")
            # Fallback to simple heuristic
            if "?" in text:
                return IntentResult(Intent.ASK_JOURNAL, 0.4, {"query": text}, text)
            return IntentResult(Intent.LOG_ENTRY, 0.4, {"content": text}, text)
