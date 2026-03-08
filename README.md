# 🎯 Echoes — Decision Companion

> *Find people who've already lived the choice you're about to make — and hear what they said after the dust settled.*

Echoes surfaces retrospective human experiences to people facing life decisions. It understands *who you are* as a decision-maker, so two people facing the same choice get different stories based on their psychological profile.

---

## What's Built

### Phase 1: Data Pipeline ✅
A complete pipeline that scrapes, classifies, tags, and stores hindsight narratives from Reddit.

### Phase 2: Personality Engine ✅
The system that understands *who* is asking the question — a conversational intake that builds an 8-dimensional values profile.

---

## Architecture Overview

```
┌──────────────┐    ┌────────────────────┐    ┌──────────────┐    ┌──────────────────┐
│   SCRAPE     │──▶│    CLASSIFY         │──▶│     TAG      │──▶│  EMBED & STORE   │
│              │    │                    │    │              │    │                  │
│ Reddit/PRAW  │    │ Stage 1: Heuristic │    │ Gemini Flash │    │ OpenAI Embeddings│
│ → SQLite     │    │ Stage 2: Gemini    │    │ → Metadata   │    │ → Qdrant Vectors │
│   (raw)      │    │   → SQLite         │    │   → SQLite   │    │   → SQLite       │
└──────────────┘    └────────────────────┘    └──────────────┘    └──────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────┐
│                        PERSONALITY ENGINE (Phase 2)                               │
│                                                                                  │
│   ┌───────────────────┐    ┌──────────────────┐    ┌──────────────────┐         │
│   │ Conversational    │──▶│ Values Vector    │──▶│ Profile Store    │         │
│   │ Intake (Gemini)   │    │ Parser           │    │ (PostgreSQL)     │         │
│   │ 5-7 adaptive Qs   │    │ 8 dimensions     │    │ Versioned        │         │
│   └───────────────────┘    └──────────────────┘    └──────────────────┘         │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### The 8 Values Dimensions

| Dimension | Low (0.0) | High (1.0) |
|-----------|-----------|------------|
| `risk_tolerance` | Risk-averse | Risk-seeking |
| `change_orientation` | Stability-seeking | Change-seeking |
| `security_vs_growth` | Security-driven | Growth-driven |
| `action_bias` | Deliberate/wait | Act fast |
| `social_weight` | Independent | Relationally-driven |
| `time_horizon` | Present-focused | Future-focused |
| `loss_sensitivity` | Loss-fearful | Gain-excited |
| `ambiguity_tolerance` | Needs clarity | Comfortable with grey |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker (for Qdrant + PostgreSQL)
- Google API key ([get one here](https://aistudio.google.com/app/apikey))
- Reddit API credentials (for full pipeline)

### 2. Setup

```bash
# Clone and enter
cd Echoes

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys

# Start services (Qdrant + PostgreSQL)
docker compose up -d
```

### 3. Run the Personality Intake (Phase 2)

```bash
# Interactive intake conversation
python scripts/run_intake.py

# Run without saving to database
python scripts/run_intake.py --no-save

# Browse saved profiles
python scripts/inspect_profiles.py
python scripts/inspect_profiles.py --user-id <UUID>
```

### 4. Run the Data Pipeline (Phase 1)

```bash
# Full pipeline (scrape → classify → tag → embed)
python scripts/run_pipeline.py

# Demo with sample data (no Reddit API needed)
python scripts/demo.py

# Just scrape Reddit
python scripts/run_scraper.py
```

### 5. Inspect Results

```bash
# Database summary
python scripts/inspect_db.py

# Items by status
python scripts/inspect_db.py --status tagged

# Sample stories with metadata
python scripts/inspect_db.py --sample 10
```

---

## Project Structure

```
Echoes/
├── config/
│   ├── settings.py           # All configuration (env vars, defaults)
│   └── logging_config.py     # Structured logging with rich formatting
├── llm/
│   ├── base_client.py        # Abstract LLM interface (Phase 1 + 2 methods)
│   └── gemini_client.py      # Gemini Flash implementation
├── scrapers/
│   ├── base_scraper.py       # Abstract base class
│   └── reddit_scraper.py     # PRAW-based Reddit scraper
├── classifiers/
│   ├── heuristic_filter.py   # Stage 1: rule-based fast filter
│   └── llm_classifier.py     # Stage 2: Gemini-powered classifier
├── processors/
│   ├── tagger.py             # Metadata extraction via Gemini
│   ├── chunker.py            # Text chunking for long narratives
│   └── embedder.py           # OpenAI embedding generation
├── storage/
│   ├── models.py             # Pydantic data models
│   ├── sqlite_store.py       # SQLite staging DB
│   └── qdrant_store.py       # Qdrant vector DB interface
├── personality/                   # Phase 2 — Personality Engine
│   ├── intake/
│   │   ├── conversation_manager.py  # Multi-turn intake orchestrator
│   │   ├── system_prompts.py        # Intake LLM persona & question bank
│   │   ├── vector_parser.py         # Defensive [VALUES_VECTOR] JSON parser
│   │   └── intake_config.py         # Turn limits, retry settings
│   ├── models/
│   │   ├── values_vector.py         # 8-dimension ValuesVector model
│   │   └── user_profile.py          # UserProfile + versioning models
│   ├── storage/
│   │   ├── postgres_store.py        # Async PostgreSQL profile store
│   │   └── migrations/
│   │       └── 001_create_profiles.sql
│   ├── api/
│   │   ├── profile_api.py           # Profile CRUD operations
│   │   └── similarity.py            # Cosine similarity computations
│   └── tests/
│       ├── test_vector_parser.py   # 23 parser edge-case tests
│       ├── test_similarity.py      # 15 similarity math tests
│       ├── test_intake.py          # 6 intake flow integration tests
│       └── test_profile_store.py   # PostgreSQL tests (skipped w/o DB)
├── pipeline/
│   └── orchestrator.py       # End-to-end pipeline coordinator
├── scripts/
│   ├── run_pipeline.py       # CLI: full pipeline
│   ├── run_intake.py         # CLI: personality intake
│   ├── inspect_profiles.py   # CLI: browse user profiles
│   ├── demo.py               # CLI: demo with sample data
│   └── inspect_db.py         # CLI: browse stored data
├── tests/
├── data/
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## Configuration

All settings live in `config/settings.py` and can be overridden via environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_API_KEY` | Gemini API key | *required* |
| `REDDIT_CLIENT_ID` | Reddit API app ID | *required for scraping* |
| `REDDIT_CLIENT_SECRET` | Reddit API secret | *required for scraping* |
| `QDRANT_HOST` | Qdrant server host | `localhost` |
| `QDRANT_PORT` | Qdrant server port | `6333` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | PostgreSQL database | `echoes` |
| `POSTGRES_USER` | PostgreSQL user | `echoes` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `echoes_dev` |

---

## Testing

```bash
# Run Phase 2 tests (no external services needed)
python -m pytest personality/tests/ -v

# Run all tests
python -m pytest tests/ personality/tests/ -v

# Run with coverage
python -m pytest personality/tests/ --cov=personality --cov-report=term-missing
```

---

## Cost Estimates

| Component | Model | Cost |
|-----------|-------|------|
| Classification | Gemini 2.5 Flash | ~$0.50 per 10K posts |
| Tagging | Gemini 2.5 Flash | ~$1.00 per 10K posts |
| Embedding | OpenAI text-embedding-3-small | ~$0.10 per 10K posts |
| Intake | Gemini 2.5 Flash | <$0.01 per session |
| **Total Pipeline** | | **~$1.60 per 10K posts** |

---

## Design Decisions

1. **SQLite as checkpoint** — Not just storage, but a crash-recovery system. Every item's status tracks its pipeline progress.

2. **Two-stage classification** — Heuristics for bulk filtering (free), LLM for nuance (cheap). Saves ~65% on API costs.

3. **LLM abstraction layer** — All Gemini calls go through `BaseLLMClient`. Swap to Claude/GPT by implementing a new client — zero pipeline changes.

4. **Conversational intake** — Not a quiz, not a form. A 5-7 question adaptive conversation that feels like talking to a thoughtful friend.

5. **Values as individual columns** — PostgreSQL stores each dimension as a separate column. Enables SQL-level filtering and cosine similarity queries for Phase 3.

6. **Defensive JSON parsing** — LLMs are unreliable JSON generators. The vector parser handles markdown fences, trailing commas, string-typed floats, missing fields, and more.

7. **Profile versioning** — Every update snapshots the old values. Profiles evolve over time as users come back with new decisions.

---

## What's Next (Phase 3: RAG Core)

Phase 3 connects the dots:
- **Phase 1**: Qdrant full of classified, tagged, embedded retrospective stories
- **Phase 2**: PostgreSQL with user profiles containing 8-dimensional values vectors
- **Phase 3**: Personality-weighted retrieval — when you describe a decision, Echoes combines your values vector with semantic search to find the stories that matter *to you*

---

*Built with care, because the person three years from now — wondering if they should leave or stay — deserves stories that are genuinely retrospective, genuinely relevant, and genuinely human.*

