"""
Greenlight Cinema — FastAPI Server v2
=======================================
API endpoints for:
 - Multi-agent synopsis generation (LangGraph)
 - DuckDB analytics queries
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from greenlight.agents.core import generate_synopsis
from greenlight.analytics.engine import AnalyticsEngine
from greenlight.config import TARGET_SCORE

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("greenlight.api")

# Global analytics instance
analytics = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events."""
    global analytics
    log.info("Starting Greenlight API v2 ...")
    analytics = AnalyticsEngine()
    if not analytics.is_healthy():
        log.warning("DuckDB is not healthy. Run setup_data.py first.")
    else:
        log.info("DuckDB analytics engine ready.")
    yield
    log.info("Shutting down API...")


app = FastAPI(title="Greenlight Cinema API v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ──────────────────────────────────────────────────────────────────

class GenerationRequest(BaseModel):
    genre: str
    budget: int = 0
    user_prompt: str = ""
    max_iterations: int = 3

class GenerationResponse(BaseModel):
    synopsis: str
    score: float
    iterations: int
    critique: dict
    constraints: dict
    budget_breakdown: dict
    risk_score: float

class SimplifyRequest(BaseModel):
    synopsis: str

class SimplifyResponse(BaseModel):
    simplified_synopsis: str


# ── Generation Endpoint ─────────────────────────────────────────────────────

@app.post("/api/generate", response_model=GenerationResponse)
async def api_generate(req: GenerationRequest):
    """Run the multi-agent synopsis generator."""
    if not analytics.is_healthy():
        raise HTTPException(status_code=503, detail="Analytics database not initialized")

    try:
        result = generate_synopsis(
            genre=req.genre,
            budget=req.budget,
            user_prompt=req.user_prompt,
            max_iterations=req.max_iterations,
        )

        if result.get("status") == "failed":
            raise Exception(result.get("error", "Unknown pipeline error occurred."))

        return GenerationResponse(
            synopsis=result.get("synopsis", ""),
            score=result.get("score", 0.0),
            iterations=result.get("iteration", 0),
            critique=result.get("critique", {}),
            constraints=result.get("constraints", {}),
            budget_breakdown=result.get("budget_breakdown", {}),
            risk_score=result.get("risk_score", 0.0),
        )
    except Exception as e:
        log.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simplify", response_model=SimplifyResponse)
async def api_simplify(req: SimplifyRequest):
    """Simplify a generated synopsis."""
    from langchain_ollama import ChatOllama
    from greenlight.config import OLLAMA_MODEL, OLLAMA_BASE_URL
    from langchain_core.messages import SystemMessage, HumanMessage
    import re
    
    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
        )
        
        system_msg = SystemMessage(content="You are an expert copywriter. Your job is to rewrite the provided movie synopsis to make it extremely easy to understand. Use plain language, short sentences, and a 5th-grade reading level. Remove all complex industry jargon. You can summarize slightly, but retain the full narrative structure and key plot points so it doesn't feel like a tiny summary. DO NOT INCLUDE TITLES OR HEADERS. ONLY output the simplified synopsis text.")
        human_msg = HumanMessage(content=f"Original Synopsis:\n\n{req.synopsis}\n\nRewrite this to be simple and easy to read, maintaining the full narrative structure:")
        
        response = llm.invoke([system_msg, human_msg])
        simplified = response.content.strip()
        
        # Clean tags
        simplified = simplified.replace('<|im_end|>', '').replace('<|endoftext|>', '').replace('<|im_start|>', '').strip()
        simplified = re.sub(r'<think>.*?</think>', '', simplified, flags=re.DOTALL).strip()
        
        return SimplifyResponse(simplified_synopsis=simplified)
    except Exception as e:
        log.error(f"Simplify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ── Analytics Endpoints ─────────────────────────────────────────────────────

@app.get("/api/analytics/genre_roi")
async def api_genre_roi():
    return analytics.get_genre_roi()

@app.get("/api/analytics/seasonal")
async def api_seasonal():
    return analytics.get_seasonal_trends()

@app.get("/api/analytics/directors")
async def api_directors():
    return analytics.get_top_directors()

@app.get("/api/analytics/actors")
async def api_actors():
    return analytics.get_top_actors()

@app.get("/api/analytics/emerging")
async def api_emerging():
    return analytics.get_emerging_talent()

@app.get("/api/analytics/budget_tiers")
async def api_budget_tiers():
    return analytics.get_budget_tiers()

@app.get("/api/analytics/genre_trends")
async def api_genre_trends(genre: str = None):
    return analytics.get_genre_trends(genre)

@app.get("/api/analytics/studios")
async def api_studios():
    return analytics.get_studio_rankings()


# ── Health Endpoint ─────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    from greenlight.rag.retriever import RAGRetriever
    rag = RAGRetriever()
    
    return {
        "status": "ok",
        "duckdb_healthy": analytics.is_healthy(),
        "chromadb_healthy": rag.is_healthy(),
        "rag_docs": rag.get_collection_count() if rag.is_healthy() else 0,
        "target_score": TARGET_SCORE
    }
