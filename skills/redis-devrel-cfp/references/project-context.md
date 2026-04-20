# Project Context

This skill is grounded in the `voice_ai_redis_memory_demo` repository.

## What the demo is

- A voice-first journaling application.
- Built to show how Redis Agent Memory Server can power long-term memory, session continuity, and semantic retrieval in a personal assistant.
- Includes a web frontend, a FastAPI backend, voice transcription and playback, Redis-backed journal storage, and memory-aware response generation.

## Stack

- Frontend: Next.js 16 and React 19
- Backend: FastAPI
- Memory layer: Redis Agent Memory Server
- Data store: Redis Cloud or Redis Stack
- Voice: Sarvam AI STT and TTS
- Intent routing: RedisVL with embeddings
- Optional response generation: local Ollama model
- Optional external context: Google Calendar

## Architecture Summary

1. The frontend captures typed or recorded input.
2. FastAPI handles the request and uses Sarvam for speech-to-text when audio is provided.
3. A voice journal agent routes the request with a RedisVL semantic intent router.
4. The agent reads and writes memory through Redis Agent Memory Server.
5. Journal data is stored in Redis for retrieval and recall.
6. Responses can be generated with an optional local Ollama model and returned as text plus TTS audio.

## Good Redis Angles for CFPs

- Giving conversational apps memory across sessions
- Combining working memory and long-term memory in Redis-backed AI systems
- Using semantic routing to separate journal logging, journal recall, and calendar queries
- Building voice AI demos that feel stateful rather than stateless
- Showing how Redis supports retrieval, memory continuity, and agent orchestration patterns in one demo

## Claims That Are Safe

- The demo is voice-first and memory-aware.
- Redis Agent Memory Server is used for long-term and working memory access.
- Redis stores journal data and supports retrieval-oriented flows.
- RedisVL is used for intent-aware routing.
- Ollama is optional and can be used locally for conversational responses.

## Claims to Avoid Unless the User Provides Proof

- Specific latency improvements or percentages
- Production readiness claims
- Scale or throughput numbers
- Security, compliance, or enterprise guarantees
- Claims that a local model is always faster or better than hosted models

## Suggested Narrative

Start with the common limitation of stateless chat and voice demos. Then show how Redis-backed memory and routing make the assistant capable of remembering prior journal entries, handling follow-up questions, and producing more contextual responses. End with the practical architecture developers can reuse in their own AI assistants.
