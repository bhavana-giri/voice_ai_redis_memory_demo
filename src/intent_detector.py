"""Intent types for voice journal commands.

Only Intent enum and IntentResult dataclass are used.
Actual intent detection is done by RedisVL SemanticRouter in intent_router.py.
"""
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class Intent(Enum):
    """Supported intents for voice journal."""
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
