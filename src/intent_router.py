"""Semantic Router for intent detection using RedisVL.

Uses embeddings to match user queries to intents - faster than LLM, more accurate than keywords.
"""

import os
from typing import Optional, Tuple
from dotenv import load_dotenv
from redisvl.extensions.router import SemanticRouter, Route
from redisvl.utils.vectorize import OpenAITextVectorizer

load_dotenv()

# Define routes with example utterances
LOG_ROUTE = Route(
    name="log",
    references=[
        "log my note",
        "log my note I had a great day",
        "note this down",
        "note this down meeting went well",
        "record this",
        "journal this",
        "save this entry",
        "remember this",
        "remember this call mom later",
        "add to my journal",
        "write this down",
        "make a note",
        "log entry",
        "I want to log something",
        "let me note that",
        "save this thought",
        "jot this down",
    ],
    metadata={"action": "save_journal"},
)

CALENDAR_ROUTE = Route(
    name="calendar",
    references=[
        "what's on my calendar",
        "what's my schedule",
        "do I have any meetings",
        "what events do I have",
        "am I free today",
        "am I busy",
        "what appointments do I have",
        "check my calendar",
        "when is my next meeting",
        "what's scheduled for today",
        "show my schedule",
        "any meetings today",
        "what time is my meeting",
        "calendar for this week",
        "do I have anything scheduled",
    ],
    metadata={"action": "fetch_calendar"},
)

CHAT_ROUTE = Route(
    name="chat",
    references=[
        "what did I do yesterday",
        "how was my day",
        "tell me about my week",
        "what have I been working on",
        "summarize my journal",
        "what did I write about",
        "find my notes about",
        "search my journal",
        "what did I mention about",
        "remind me what I said",
        "how have I been feeling",
        "what were my thoughts on",
    ],
    metadata={"action": "search_journal"},
)


class IntentRouter:
    """Semantic router for fast, accurate intent detection."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL")
        self._router: Optional[SemanticRouter] = None
        self._initialized = False

    def _init_router(self):
        """Initialize the semantic router (lazy load)."""
        if self._initialized:
            return

        vectorizer = OpenAITextVectorizer(
            model="text-embedding-3-small",
            api_config={"api_key": os.getenv("OPENAI_API_KEY")},
        )

        self._router = SemanticRouter(
            name="intent_router",
            routes=[LOG_ROUTE, CALENDAR_ROUTE, CHAT_ROUTE],
            vectorizer=vectorizer,
            redis_url=self.redis_url,
            overwrite=True,  # Rebuild on startup for fresh embeddings
        )
        self._initialized = True
        print("[IntentRouter] Initialized with semantic routes")

    def detect(self, text: str, distance_threshold: float = 0.5) -> Tuple[str, float]:
        """
        Detect intent from text using semantic similarity.

        Returns:
            Tuple of (intent_name, confidence_score)
            intent_name: "log", "calendar", "chat", or "unknown"
        """
        if not self._initialized:
            self._init_router()

        result = self._router(text, distance_threshold=distance_threshold)

        if result and result.name:
            # Convert distance to confidence (lower distance = higher confidence)
            confidence = 1.0 - (result.distance or 0.0)
            return result.name, confidence

        return "chat", 0.5  # Default to chat with medium confidence


# Singleton instance
_router_instance: Optional[IntentRouter] = None


def get_intent_router() -> IntentRouter:
    """Get or create singleton router instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntentRouter()
    return _router_instance

