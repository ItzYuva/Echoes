# 🎯 Echoes — Phase 1: Data Pipeline & Retrospective Classifier

> *Find people who've already lived the choice you're about to make — and hear what they said after the dust settled.*

Echoes surfaces retrospective human experiences to people facing life decisions. Phase 1 is the data foundation: a complete pipeline that scrapes, classifies, tags, and stores hindsight narratives from Reddit.

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
```

### The Two-Stage Classifier

The classifier is the most critical quality gate:

1. **Stage 1 — Heuristic Filter** (free, fast): 40+ weighted regex signals scan for temporal markers ("years ago", "looking back"), outcome language ("turned out", "best decision"), and negative signals ("should I?", "help me"). Filters out ~60-70% of non-retrospective content.

2. **Stage 2 — Gemini 2.0 Flash** (cheap, accurate): LLM-based classification for borderline cases. Cost: ~$0.50 for 10,000 posts.

### Pipeline Status Flow

Every item tracks its progress in SQLite:

```
raw → heuristic_pass → classified_retrospective → tagged → indexed
              ↓                    ↓                 ↓
      rejected_heuristic    rejected_llm         failed
                             needs_review
```

If the pipeline crashes, restart it — it picks up exactly where it left off.

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker (for Qdrant)
- Reddit API credentials ([create app here](https://www.reddit.com/prefs/apps))
- Google API key ([get one here](https://aistudio.google.com/app/apikey))
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

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

# Start Qdrant
docker compose up -d
```

### 3. Run

```bash
# Full pipeline (scrape → classify → tag → embed)
python scripts/run_pipeline.py

# Just scrape Reddit
python scripts/run_scraper.py

# Skip scraping, process existing data
python scripts/run_pipeline.py --no-scrape

# Only re-classify (after tweaking heuristic)
python scripts/run_pipeline.py --classify-only

# Only re-tag metadata
python scripts/run_pipeline.py --tag-only

# Only re-embed and store
python scripts/run_pipeline.py --embed-only

# Scrape specific subreddit
python scripts/run_scraper.py --subreddit AskReddit --limit 100

# Debug logging
python scripts/run_pipeline.py --debug
```

### 4. Inspect Results

```bash
# Database summary
python scripts/inspect_db.py

# Items by status
python scripts/inspect_db.py --status tagged

# Sample stories with metadata
python scripts/inspect_db.py --sample 10

# Specific item details
python scripts/inspect_db.py --item <uuid>

# Qdrant collection info
python scripts/inspect_db.py --qdrant
```

### 5. Validate the Classifier

```bash
# Create labeled samples
python scripts/seed_labels.py

# Test heuristic accuracy against labels
python scripts/seed_labels.py --validate
```

---

## Project Structure

```
Echoes/
├── config/
│   ├── settings.py           # All configuration (env vars, subreddit lists, thresholds)
│   └── logging_config.py     # Structured logging with rich formatting
├── llm/
│   ├── base_client.py        # Abstract LLM interface (swap-friendly)
│   └── gemini_client.py      # Gemini 2.0 Flash implementation
├── scrapers/
│   ├── base_scraper.py       # Abstract base class (extensible)
│   └── reddit_scraper.py     # PRAW-based Reddit scraper
├── classifiers/
│   ├── heuristic_filter.py   # Stage 1: rule-based fast filter (40+ signals)
│   └── llm_classifier.py     # Stage 2: Gemini-powered classifier
├── processors/
│   ├── tagger.py             # Metadata extraction via Gemini
│   ├── chunker.py            # Text chunking for long narratives
│   └── embedder.py           # OpenAI embedding generation
├── storage/
│   ├── models.py             # Pydantic data models (source of truth)
│   ├── sqlite_store.py       # SQLite staging DB (checkpoint system)
│   └── qdrant_store.py       # Qdrant vector DB interface
├── pipeline/
│   └── orchestrator.py       # End-to-end pipeline coordinator
├── scripts/
│   ├── run_scraper.py        # CLI: scrape only
│   ├── run_pipeline.py       # CLI: full pipeline
│   ├── inspect_db.py         # CLI: browse stored data
│   └── seed_labels.py        # CLI: create/validate labeled samples
├── tests/
│   ├── test_classifier.py    # Heuristic + LLM classifier tests
│   ├── test_tagger.py        # Metadata parsing tests
│   └── test_pipeline.py      # Integration tests
├── data/
│   ├── labeled_samples/      # Hand-labeled examples
│   └── staging.db            # SQLite database (gitignored)
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
| `REDDIT_CLIENT_ID` | Reddit API app ID | *required* |
| `REDDIT_CLIENT_SECRET` | Reddit API secret | *required* |
| `GOOGLE_API_KEY` | Gemini API key | *required* |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | *required* |
| `QDRANT_HOST` | Qdrant server host | `localhost` |
| `QDRANT_PORT` | Qdrant server port | `6333` |

---

## Example Pipeline Output

Here's what a processed story looks like:

```json
{
  "text": "Three years after leaving that corporate job, I can honestly say it was the best decision I ever made. At the time I was terrified — I had a mortgage, two kids, and everyone told me I was insane. But looking back, the fear of leaving was so much worse than anything that actually happened after...",
  "source": "reddit",
  "subreddit": "r/careerguidance",
  "author_hash": "a1b2c3d4e5...",
  "scraped_at": "2025-01-15T10:30:00Z",
  "original_score": 342,
  "decision_type": "career",
  "decision_subcategory": "leaving a job",
  "outcome_sentiment": "positive",
  "time_elapsed_months": 36,
  "emotional_richness": 8,
  "outcome_clarity": true,
  "key_themes": ["fear of unknown", "growth", "work-life balance"],
  "hindsight_insight": "The fear of leaving was worse than anything that actually happened after.",
  "classification_confidence": "RETROSPECTIVE",
  "chunk_index": 0,
  "total_chunks": 1
}
```

---

## Cost Estimates

| Component | Model | Cost |
|-----------|-------|------|
| Classification | Gemini 2.0 Flash | ~$0.50 per 10K posts |
| Tagging | Gemini 2.0 Flash | ~$1.00 per 10K posts |
| Embedding | OpenAI text-embedding-3-small | ~$0.10 per 10K posts |
| **Total** | | **~$1.60 per 10K posts** |

The heuristic filter saves 60-70% of classification costs by filtering obvious non-retrospective content for free.

---

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_classifier.py -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=term-missing
```

---

## Design Decisions

1. **SQLite as checkpoint** — Not just storage, but a crash-recovery system. Every item's status tracks its pipeline progress.

2. **Two-stage classification** — Heuristics for bulk filtering (free), LLM for nuance (cheap). Saves ~65% on API costs.

3. **LLM abstraction layer** — All Gemini calls go through `BaseLLMClient`. Swap to Claude/GPT by implementing a new client — zero pipeline changes.

4. **Content hashing for dedup** — SHA-256 on normalized text. Same story from different scrape runs → same hash → skip.

5. **Async with semaphore** — Concurrent LLM calls bounded by semaphore (max 10). Balances throughput and rate limits.

6. **No over-engineering** — No Airflow, no Celery, no K8s. A Python script that runs end-to-end on one machine. We scale when we need to.

---

## What's Next (Phase 2+)

- **Personality matching** — OCEAN/DiSC profiling for story-to-user alignment
- **RAG retrieval** — Hybrid search (semantic + metadata filters) for relevant stories
- **Frontend** — The interface where someone at a crossroads meets the wisdom of hindsight
- **Additional sources** — StoryCorps, blog posts, interview transcripts

---

*Built with care, because the person three years from now — wondering if they should leave or stay — deserves stories that are genuinely retrospective, genuinely relevant, and genuinely human.*
