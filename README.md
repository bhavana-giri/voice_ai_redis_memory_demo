# Voice Journal with Redis Agent Memory Server

[![Redis Agent Memory Server](https://img.shields.io/badge/Redis-Agent%20Memory%20Server-red?logo=redis)](https://github.com/redis/agent-memory-server)
[![Sarvam AI](https://img.shields.io/badge/Sarvam%20AI-Voice-blue)](https://sarvam.ai/)
[![Next.js](https://img.shields.io/badge/Next.js-Frontend-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered voice journaling application that demonstrates how **Redis Agent Memory Server** enables long-term memory and semantic search, allowing the agent to remember your journal entries across sessions and provide personalized responses.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Start Agent Memory Server](#3-start-agent-memory-server)
  - [4. Run the Backend](#4-run-the-backend)
  - [5. Run the Frontend](#5-run-the-frontend)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Resources](#resources)
- [License](#license)

## Features

- **Voice Recording & Transcription** - Speak your journal entries using Sarvam AI Saaras v3 (supports 22 Indian languages + English)
- **Long-term Memory** - Redis Agent Memory Server stores and retrieves journal entries with semantic search
- **Working Memory** - Session-scoped context for natural conversations
- **Semantic Search** - Find past entries by meaning, not just keywords
- **Google Calendar Integration** - Ask about your schedule (read-only)
- **Mood Tracking** - Track your daily mood with journal entries
- **Real-time TTS** - Streaming text-to-speech for fast audio responses

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Memory** | [Redis Agent Memory Server](https://github.com/redis/agent-memory-server) | Long-term and working memory management |
| **Database** | [Redis Cloud](https://redis.io/cloud/) | Vector storage and session persistence |
| **Voice** | [Sarvam AI](https://sarvam.ai/) | Speech-to-text (Saaras v3) and text-to-speech (Bulbul v3) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) | Python REST API |
| **Frontend** | [Next.js 16](https://nextjs.org/) + TypeScript | User interface |
| **Styling** | [Tailwind CSS](https://tailwindcss.com/) | UI styling |
| **LLM** | [Ollama](https://ollama.ai/) (local) | Natural language responses |
| **Intent Detection** | [RedisVL](https://github.com/redis/redis-vl-python) + [OpenAI Embeddings](https://openai.com/) | Semantic router for fast intent classification |

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** (for Agent Memory Server)
- **Ollama** (for local LLM) - [Install here](https://ollama.ai/)
- **Redis Cloud account** or local Redis instance
- **API Keys:**
  - [Sarvam AI API Key](https://console.sarvam.ai/)
  - [OpenAI API Key](https://platform.openai.com/api-keys) (for embeddings only)

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/bhavana-giri/voice_ai_redis_memory_demo.git
cd voice_ai_redis_memory_demo
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Sarvam AI API Key (for Speech-to-Text and Text-to-Speech)
SARVAM_API_KEY=your_sarvam_api_key_here

# Redis Cloud Connection URL
REDIS_URL=redis://default:your_password@your-redis-host.cloud.redislabs.com:12345

# Agent Memory Server URL
MEMORY_SERVER_URL=http://localhost:8000

# OpenAI API Key (for semantic router embeddings)
OPENAI_API_KEY=sk-your_openai_api_key_here

# Ollama (for LLM responses - install from https://ollama.ai/)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Create frontend environment file:

```bash
cp frontend/.env.local.example frontend/.env.local
```

### 3. Start Agent Memory Server

Get the pre-built Docker image from [Docker Hub](https://hub.docker.com/r/redislabs/agent-memory-server):

```bash
docker run -p 8000:8000 \
  -e REDIS_URL=redis://default:<password>@<your-redis-host>:<port> \
  -e OPENAI_API_KEY=<your-openai-api-key> \
  redislabs/agent-memory-server:latest \
  agent-memory api --host 0.0.0.0 --port 8000 --task-backend=asyncio
```

> **Note:** You must have a running Redis instance (e.g., Redis Cloud) accessible at the URL you provide.

### 4. Run the Backend

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional dependencies for voice
pip install sarvamai openai fastapi uvicorn python-multipart redisvl

# Run the FastAPI server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8080
```

The backend API will be available at: http://localhost:8080

### 5. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at: http://localhost:3000

## Architecture

```mermaid
flowchart LR
    subgraph User["👤 User"]
        MIC[🎤 Voice]
        SPEAKER[🔊 Audio]
    end

    subgraph App["Voice Journal App"]
        FE[Next.js<br/>Frontend]
        BE[FastAPI<br/>Backend]
        AGENT[Voice Agent]
    end

    subgraph AI["AI Services"]
        STT[Sarvam STT]
        TTS[Sarvam TTS]
        LLM[Ollama]
        ROUTER[RedisVL<br/>Intent Router]
    end

    subgraph Memory["Redis Agent Memory Server"]
        WM[Working Memory]
        LTM[Long-term Memory]
    end

    subgraph Storage["Redis Cloud"]
        VEC[(Vectors)]
    end

    MIC --> FE --> BE
    BE --> STT --> AGENT
    AGENT --> ROUTER
    AGENT --> LLM
    AGENT <--> WM
    AGENT <--> LTM
    WM --> VEC
    LTM --> VEC
    AGENT --> TTS --> BE --> FE --> SPEAKER
```

## Project Structure

```
voice_ai_redis_memory_demo/
├── api/
│   └── main.py              # FastAPI application with all endpoints
├── src/
│   ├── audio_handler.py     # Sarvam AI STT/TTS integration
│   ├── voice_agent.py       # Main conversational agent
│   ├── memory_client.py     # Redis Agent Memory Server client
│   ├── intent_router.py     # RedisVL semantic router
│   ├── calendar_client.py   # Google Calendar integration
│   ├── journal_manager.py   # Journal entry management
│   ├── journal_store.py     # Local journal storage
│   └── analytics.py         # Journal analytics
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js app router
│   │   └── components/      # React components
│   ├── package.json
│   └── .env.local.example
├── tests/
│   └── test_journal.py      # Unit tests
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── README.md
```

## Usage

1. **Open the app** at http://localhost:3000

2. **Record a journal entry** - Click the microphone button and speak your thoughts

3. **Chat with your journal** - Ask questions like:
   - "What did I do yesterday?"
   - "How have I been feeling this week?"
   - "Summarize my journal"

4. **Check your calendar** - Ask:
   - "What's on my calendar today?"
   - "Do I have any meetings?"

5. **Log notes quickly** - Say:
   - "Note this down: call mom tomorrow"
   - "Remember that I need to buy groceries"

The agent remembers your entries across sessions, so you can return anytime and ask about past entries.

## Resources

- [Redis Agent Memory Server](https://github.com/redis/agent-memory-server)
- [Sarvam AI Documentation](https://docs.sarvam.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [Redis Cloud](https://redis.io/cloud/)
- [RedisVL Documentation](https://redis.io/docs/latest/integrate/redisvl/)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
