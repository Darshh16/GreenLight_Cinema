# Greenlight Cinema

**AI-Powered Movie Synopsis Generation with Market Intelligence**

Greenlight Cinema combines historical movie performance analytics with agentic AI workflows to generate commercially-aware movie synopses. It analyzes TMDB and MovieLens datasets, extracts commercial insights, and uses a multi-agent system (Writer -> Critic -> Refiner -> Producer) to generate, evaluate, refine, and financially assess market-aware movie synopses.

## Core Features

- **Historical Data Analytics**: Uses DuckDB to query massive TMDB & MovieLens datasets, uncovering true ROI trends, seasonal sweet spots, and high-value casting combinations for your specific genre.
- **Dynamic Market Constraints**: Automatically generates mandatory storytelling constraints based on the chosen budget tier (e.g., Q4 awards push vs. Q2 summer blockbuster).
- **Advanced RAG (Retrieval-Augmented Generation)**: Uses ChromaDB and Sentence Transformers to retrieve stylistically similar, pacing-perfect screenplay excerpts to influence the tone of the generation.
- **Agentic Multi-LLM Workflow**: Powered by LangGraph, it features a self-correcting loop of four specialized agents:
  - **Writer**: Drafts a compelling 3-act synopsis, strictly enforcing physical logic and character state continuity.
  - **Critic**: Harshly scores the draft based on market constraint adherence, pacing, and logic.
  - **Refiner**: Surgically rewrites failing sections to improve the score without breaking the story's continuity.
  - **Producer**: Calculates a realistic budget breakdown across departments and outputs a final Greenlight Risk Score.
- **Sleek UI Dashboard**: An interactive Streamlit frontend with real-time polling, modern typography, percentage-based risk tracking, and dynamic visual progress bars.

## Architecture

```text
TMDB + MovieLens -> DuckDB -> Analytics Engine -> Constraint Engine
                                                      |
ChromaDB <- Sentence Transformers <- Movie Overviews  |
     |                                                |
    RAG -> LangGraph (Writer -> Critic -> Refiner -> Producer) <- Ollama (qwen3:4b)
                        |
                    FastAPI -> Streamlit Dashboard
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Data Pipeline
```bash
# Full setup: clean data + load DuckDB + ingest ChromaDB
python scripts/setup_data.py

# Skip RAG ingestion (faster, for testing analytics only)
python scripts/setup_data.py --skip-rag
```

### 3. Start the API
```bash
uvicorn greenlight.api.main:app --host 0.0.0.0 --port 8000
```

### 4. Start the Dashboard
```bash
streamlit run frontend/app.py
```

### 5. Verify System Health
```bash
python scripts/run_health_check.py
```

## Project Structure

```text
greenlight-cinema/
├── data/                           # Raw CSV datasets
│   ├── tmdb.csv                    # TMDB movie metadata (638 MB)
│   ├── credits.csv                 # Cast & crew (190 MB)
│   ├── links.csv                   # MovieLens <-> TMDB mapping (2 MB)
│   ├── movies.csv                  # MovieLens movies (4 MB)
│   ├── ratings.csv                 # 33M+ ratings (934 MB)
│   └── tags.csv                    # User tags (85 MB)
├── greenlight/                     # Main Python package
│   ├── config.py                   # Centralized configuration
│   ├── data/                       # M1: Data cleaning & loading
│   │   ├── clean.py                # CSV cleaning pipeline
│   │   └── load.py                 # DuckDB loader + derived tables
│   ├── analytics/                  # M2: Analytics & constraints
│   │   ├── engine.py               # DuckDB query engine
│   │   └── constraints.py          # Market constraint generator
│   ├── rag/                        # M3: RAG pipeline
│   │   ├── ingest.py               # ChromaDB ingestion
│   │   └── retriever.py            # Similarity retrieval
│   ├── agents/                     # M4: LangGraph agents
│   │   ├── state.py                # Graph state definition
│   │   ├── writer.py               # Synopsis writer agent
│   │   ├── critic.py               # Evaluation critic agent
│   │   ├── refiner.py              # Targeted refinement agent
│   │   ├── producer.py             # Studio Producer agent (budget & risk scoring)
│   │   └── graph.py                # LangGraph workflow
│   ├── validation/                 # Constraint validation
│   │   └── validator.py            # Validation engine
│   └── api/                        # M5: FastAPI backend
│       ├── main.py                 # API endpoints
│       ├── models.py               # Pydantic schemas
│       └── jobs.py                 # Job management
├── frontend/                       # M6: Streamlit dashboard
│   └── app.py
├── scripts/
│   ├── setup_data.py               # Full data setup
│   ├── run_health_check.py         # Health verification
│   ├── rag_pipeline.py             # RAG pipeline for downloading and ingesting scripts
│   └── run_ingest.py               # Targeted ChromaDB ingestion script
├── scrape_imsdb.py                 # Scraper for IMSDb screenplays
├── requirements.txt
├── .env.example
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate-synopsis` | Submit generation job |
| GET | `/status/{job_id}` | Poll job status |
| GET | `/constraints` | Get constraint template |
| GET | `/analytics/genre-roi` | Genre ROI data |
| GET | `/analytics/seasonal` | Seasonal trends |
| GET | `/analytics/directors` | Director rankings |
| GET | `/analytics/actors` | Actor rankings |
| GET | `/analytics/budget-tiers` | Budget tier analysis |
| GET | `/health` | System health check |

## Tech Stack

- **Data**: DuckDB, Pandas, NumPy
- **RAG**: ChromaDB, Sentence Transformers (all-MiniLM-L6-v2)
- **LLM**: Ollama (qwen3:4b)
- **Agents**: LangGraph, LangChain
- **API**: FastAPI, Pydantic, slowapi
- **Frontend**: Streamlit, Plotly
