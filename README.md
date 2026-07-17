<div align="center">

#  Greenlight Cinema

### AI-Powered Movie Synopsis Generation with Market Intelligence

*Where data drives creativity — and every synopsis is commercially validated before it's written.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent_Workflow-7B61FF?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![DuckDB](https://img.shields.io/badge/DuckDB-Analytics-FFC832?style=flat-square)](https://duckdb.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange?style=flat-square)](https://www.trychroma.com)

</div>

---

## What is Greenlight Cinema?

Hollywood greenlights films on gut feel, market experience, and subjective judgement. **Greenlight Cinema changes that.**

It combines historical movie performance analytics with an agentic AI workflow to generate movie synopses that are not just creative — but commercially validated. Every synopsis is scored against real ROI data, seasonal release windows, and genre performance trends before it ever reaches a human reader.

The system analyzes **77,000+ TMDB films** and **33 million MovieLens ratings**, extracts commercial constraints, and runs them through a self-correcting loop of four specialized AI agents — Writer, Critic, Refiner, and Producer — each with a distinct job, each accountable to the market data.

---

## How It Works

```
TMDB + MovieLens (33M+ ratings)
         │
         ▼
    DuckDB Analytics Engine
    ├── Genre ROI rankings
    ├── Seasonal release trends
    ├── Director performance
    └── Actor commercial value
         │
         ▼
    Constraint Engine
    {"top_genres": ["Action"], "seasonal_fit": "Q4", "target_roi": 4.2}
         │
         ├─────────────────────────────────────────┐
         ▼                                         ▼
  ChromaDB RAG                              User Input
  (20k+ screenplay chunks)                 Genre · Budget · Prompt
  Top 3 similar scenes retrieved
         │                                         │
         └──────────────┬──────────────────────────┘
                        ▼
              ┌─── LangGraph Workflow ───┐
              │                         │
              │   Writer Agent          │  ← Constraints + RAG examples
              │       ↓                 │
              │   Critic Agent          │  ← Scores 0–1
              │       ↓  (score < 0.7)  │
              │   Refiner Agent         │  ← Fixes violations only
              │       ↓  (loop ≤ 3×)   │
              │   Producer Agent        │  ← Budget breakdown + risk score
              └─────────────────────────┘
                        │
                        ▼
              FastAPI → Streamlit Dashboard
              Synopsis · Market Score · Budget · Risk
```

---

## Core Features

###  Historical Data Analytics
Queries 77,000+ TMDB films and 33M+ MovieLens ratings via DuckDB to surface real commercial patterns — genre ROI by budget tier, seasonal release windows, high-value director/actor combinations, and audience rating trends. All analytics use only films with genuine reported budgets and revenues, not imputed values.

###  Dynamic Market Constraints
Automatically generates JSON constraint objects from the analytics data, tuned to the user's chosen genre and budget tier. A $10M horror film gets different constraints than a $150M action blockbuster — different target ROI, different seasonal fit, different casting guidance.

###  Advanced RAG Pipeline
Uses ChromaDB and `all-MiniLM-L6-v2` sentence embeddings to store 20,000+ scene-level chunks from 100 real screenplays. At generation time, the system retrieves the 3 most semantically similar scenes to the user's prompt, giving the Writer Agent concrete stylistic and structural reference material — not just instructions.

###  Self-Correcting Multi-Agent Workflow
Four specialized agents, each with a distinct accountability:

| Agent | Responsibility | Output |
|---|---|---|
| **Writer** | Drafts a 3-act synopsis enforcing physical logic and character continuity | 300-400 word synopsis |
| **Critic** | Scores genre compliance, seasonal fit, ROI alignment, and narrative quality | Score 0–1 + issues list |
| **Refiner** | Surgically rewrites only the failing sections without breaking story continuity | Improved synopsis |
| **Producer** | Calculates realistic department-level budget breakdown and final risk score | Budget table + Greenlight Risk Score |

The Writer → Critic → Refiner loop runs up to 3 times until the score exceeds 0.7, then hands off to Producer.

###  Streamlit Dashboard
Real-time polling dashboard with market constraint visualization, agent progress tracking, synopsis display with audio narration (Web Speech API), critic evaluation scorecard, and producer budget breakdown — all in a dark cinematic UI.

---

## Quick Start

### 1. Prerequisites

```bash
# Python 3.10+
pip install -r requirements.txt

# Ollama (local LLM — no API key needed)
# Install from https://ollama.ai then pull the model:
ollama pull qwen3:4b
```

### 2. Add Data Files

Place these CSV files in the `data/` folder:

| File | Size | Source |
|---|---|---|
| `tmdb.csv` | 638 MB | TMDB dataset |
| `credits.csv` | 190 MB | TMDB credits |
| `links.csv` | 2 MB | MovieLens ↔ TMDB mapping |
| `movies.csv` | 4 MB | MovieLens movies |
| `ratings.csv` | 934 MB | MovieLens ratings (33M+) |
| `tags.csv` | 85 MB | MovieLens tags |

### 3. Run the Full Setup Pipeline

```bash
# Clean data + load DuckDB + ingest ChromaDB scripts
python scripts/setup_data.py

# Faster option — skip RAG ingestion (analytics only)
python scripts/setup_data.py --skip-rag
```

### 4. Start the Services

```bash
# Terminal 1 — FastAPI backend
uvicorn greenlight.api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — Streamlit frontend
streamlit run frontend/app.py
```

### 5. Verify Everything is Working

```bash
python scripts/run_health_check.py
```

Then open `http://localhost:8501` and generate your first synopsis.

---

## Project Structure

```
greenlight-cinema/
│
├── data/                           # Raw CSV datasets (not committed to git)
│   ├── tmdb.csv                    # TMDB movie metadata (638 MB)
│   ├── credits.csv                 # Cast & crew data (190 MB)
│   ├── links.csv                   # MovieLens ↔ TMDB ID mapping (2 MB)
│   ├── movies.csv                  # MovieLens movie titles (4 MB)
│   ├── ratings.csv                 # 33M+ audience ratings (934 MB)
│   ├── tags.csv                    # User-generated tags (85 MB)
│   └── scripts/                    # Screenplay PDFs/TXTs for RAG
│
├── greenlight/                     # Main Python package
│   ├── config.py                   # Centralized configuration & env vars
│   │
│   ├── data/                       # M1: Data cleaning & loading
│   │   ├── clean.py                # CSV filtering, ROI computation, genre parsing
│   │   └── load.py                 # DuckDB loader + derived analytics tables
│   │
│   ├── analytics/                  # M2: Analytics engine
│   │   ├── engine.py               # DuckDB query engine (genre ROI, trends, talent)
│   │   └── constraints.py          # Market constraint generator
│   │
│   ├── rag/                        # M3: RAG pipeline
│   │   ├── ingest.py               # PDF/TXT extraction, chunking, ChromaDB storage
│   │   └── retriever.py            # Semantic similarity retrieval
│   │
│   ├── agents/                     # M4: LangGraph multi-agent workflow
│   │   ├── state.py                # Shared GraphState TypedDict
│   │   ├── writer.py               # Synopsis writer agent
│   │   ├── critic.py               # Market compliance critic agent
│   │   ├── refiner.py              # Surgical refinement agent
│   │   ├── producer.py             # Budget + Greenlight Risk Score agent
│   │   └── graph.py                # LangGraph workflow definition
│   │
│   ├── validation/
│   │   └── validator.py            # Constraint validation engine
│   │
│   └── api/                        # M5: FastAPI backend
│       ├── main.py                 # Route definitions
│       ├── models.py               # Pydantic request/response schemas
│       └── jobs.py                 # Async job queue & status management
│
├── frontend/                       # M6: Streamlit dashboard
│   └── app.py                      # Full UI with polling + audio narration
│
├── scripts/
│   ├── setup_data.py               # Orchestrates full data pipeline
│   ├── run_health_check.py         # System health verification
│   ├── rag_pipeline.py             # RAG ingestion pipeline
│   └── run_ingest.py               # Targeted ChromaDB re-ingestion
│
├── scrape_imsdb.py                 # IMSDB screenplay scraper (→ data/scripts/)
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/generate-synopsis` | Submit a new synopsis generation job |
| `GET` | `/status/{job_id}` | Poll job status (queued / running / completed / failed) |
| `GET` | `/constraints` | Get market constraint template for a genre/budget |
| `GET` | `/analytics/genre-roi` | Genre ROI rankings from DuckDB |
| `GET` | `/analytics/seasonal` | Seasonal release performance trends |
| `GET` | `/analytics/directors` | Director ROI rankings (min 5 films) |
| `GET` | `/analytics/actors` | Actor commercial value rankings |
| `GET` | `/analytics/budget-tiers` | Performance by budget tier |
| `GET` | `/health` | Full system health check |

### Example Request

```bash
curl -X POST http://localhost:8000/generate-synopsis \
  -H "Content-Type: application/json" \
  -d '{
    "genre": "Action",
    "budget": 100000000,
    "prompt": "A retired hitman whose dog gets kidnapped",
    "max_iterations": 3
  }'
```

```json
{ "job_id": "a3f8c2d1-..." }
```

```bash
curl http://localhost:8000/status/a3f8c2d1-...
```

```json
{
  "status": "completed",
  "synopsis": "...",
  "market_score": 0.82,
  "iterations_used": 2,
  "budget_breakdown": { ... },
  "greenlight_risk_score": 74
}
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Data Storage** | DuckDB | In-process analytical SQL on 33M+ rows |
| **Data Processing** | Pandas, NumPy | CSV cleaning, ROI computation |
| **Vector Store** | ChromaDB | 20k+ screenplay chunk embeddings |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | 384-dim semantic search |
| **LLM** | Ollama (`qwen3:4b`) | Local inference, no API key required |
| **Agent Orchestration** | LangGraph + LangChain | Writer → Critic → Refiner → Producer loop |
| **API** | FastAPI + Pydantic | Async REST endpoints with job management |
| **Rate Limiting** | slowapi | 50 requests/min/IP |
| **Frontend** | Streamlit + Plotly | Interactive dashboard with real-time polling |

---

## Configuration

Copy `.env.example` to `.env` and adjust:

```env
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b

# Paths
DUCKDB_PATH=greenlight.duckdb
CHROMA_DIR=data/chromadb
SCRIPTS_DIR=data/scripts

# Agent settings
MAX_ITERATIONS=3
MIN_CRITIQUE_SCORE=0.7
SYNOPSIS_TARGET_WORDS=150

# API
API_HOST=0.0.0.0
API_PORT=8000
RATE_LIMIT=50/minute
```

---

## Performance Targets

| Metric | Target |
|---|---|
| Synopsis generation (end-to-end) | < 15 seconds |
| Critique score on first pass | > 0.65 |
| Critique score after refinement | > 0.70 |
| Health endpoint response | < 500 ms |
| Analytics query (DuckDB) | < 5 seconds |
| Concurrent users supported | 5+ |

---

## Development Milestones

- [x] **M1** — Data ingestion: TMDB + MovieLens → DuckDB (77k films, 33M ratings)
- [x] **M2** — Analytics engine + market constraint generator
- [x] **M3** — RAG pipeline: 100 screenplays → 20k+ ChromaDB chunks
- [x] **M4** — LangGraph agents: Writer → Critic → Refiner → Producer
- [x] **M5** — FastAPI backend with async job management
- [x] **M6** — Streamlit dashboard with real-time polling + audio narration
- [ ] **M7** — Testing suite + Docker deployment

---

## Future Enhancements

- **Human-in-the-loop** — Allow studio executives to inject feedback mid-refinement cycle
- **Multi-model voting** — Run Writer across multiple LLMs and consensus-select the best draft
- **Backtesting engine** — Score historical synopses against actual box office outcomes
- **Debate workflow** — Two Critic agents with opposing views force more robust refinement
- **Fine-tuned embeddings** — Domain-specific screenplay embeddings replacing MiniLM

---

## License

This project is for educational and research purposes.
Data sources: [TMDB](https://www.themoviedb.org/) · [MovieLens](https://grouplens.org/datasets/movielens/) · [IMSDB](https://imsdb.com/)

---

<div align="center">
  <sub>Built by Darsh and with LangGraph · DuckDB · ChromaDB · Ollama · FastAPI · Streamlit</sub>
</div>
