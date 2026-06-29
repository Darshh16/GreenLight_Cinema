"""
Greenlight Cinema — LangGraph Workflow v2
==========================================
Orchestrates the multi-agent synopsis generation:

  Prepare → Writer → Critic → [Refiner → Critic]* → End

Exit conditions:
  - score >= TARGET_SCORE (0.7)
  - iteration >= max_iterations (3)
"""

import logging
import time

from langgraph.graph import StateGraph, END

from greenlight.analytics.constraints import ConstraintEngine
from greenlight.rag.retriever import RAGRetriever
from greenlight.config import TARGET_SCORE, MAX_ITERATIONS

from greenlight.agents.state import GraphState
from greenlight.agents.writer import writer_node
from greenlight.agents.critic import critic_node
from greenlight.agents.refiner import refiner_node
from greenlight.agents.producer import producer_node

log = logging.getLogger("greenlight.agents.graph")


def _should_continue(state: GraphState) -> str:
    """Decide whether to refine or end."""
    score = state.get("score", 0.0)
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", MAX_ITERATIONS)
    status = state.get("status", "running")

    if status == "failed":
        log.info(f"Workflow ending early: status=failed")
        return "end"

    if score >= TARGET_SCORE:
        log.info(f"Workflow transitioning to producer: score {score:.3f} >= {TARGET_SCORE}")
        return "producer"

    if iteration >= max_iter:
        log.info(f"Workflow transitioning to producer: iteration {iteration} >= max {max_iter}")
        return "producer"

    log.info(f"Workflow continuing: score {score:.3f} < {TARGET_SCORE}, "
             f"iteration {iteration} < {max_iter}")
    return "refine"


def _prepare_node(state: GraphState) -> dict:
    """Prepare constraints and RAG context."""
    log.info("Preparing constraints and RAG context ...")

    genre = state["genre"]
    budget = state.get("budget", 0)
    user_prompt = state.get("user_prompt", "")

    # Generate constraints
    try:
        constraint_engine = ConstraintEngine()
        constraints_obj = constraint_engine.generate(genre, budget or None)
        constraints = constraints_obj.to_dict()
        constraints["prompt_text"] = constraints_obj.to_prompt_text()
        log.info(f"  Constraints generated for genre='{genre}', budget={budget}")
    except Exception as e:
        log.warning(f"  Constraint generation failed: {e}")
        constraints = {
            "genre": genre,
            "prompt_text": f"Genre: {genre}\nBudget: ${budget:,}" if budget else f"Genre: {genre}",
        }

    # Retrieve RAG examples — real screenplay scenes from ChromaDB
    retrieved = []
    try:
        retriever = RAGRetriever()
        if retriever.is_healthy():
            query_str = user_prompt if user_prompt else f"A compelling {genre} movie scene"
            scenes = retriever.retrieve_mixed(genre, query_str, n=5)
            for s in scenes:
                retrieved.append({
                    "document": s.document,
                    "title": s.title,
                    "source": s.source,
                    "genre": s.genre,
                    "act": s.act,
                    "year": s.year,
                })
            log.info(f"  Retrieved {len(retrieved)} screenplay chunks from ChromaDB")
        else:
            log.warning("  ChromaDB not available — continuing without RAG")
    except Exception as e:
        log.warning(f"  RAG retrieval failed: {e}")

    return {
        "constraints": constraints,
        "retrieved_examples": retrieved,
        "iteration": 1,
        "status": "running",
    }


def build_graph() -> StateGraph:
    """Build the LangGraph workflow."""
    workflow = StateGraph(GraphState)

    workflow.add_node("prepare", _prepare_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("refiner", refiner_node)
    workflow.add_node("producer", producer_node)

    workflow.set_entry_point("prepare")
    workflow.add_edge("prepare", "writer")
    workflow.add_edge("writer", "critic")

    workflow.add_conditional_edges(
        "critic",
        _should_continue,
        {"refine": "refiner", "producer": "producer", "end": END},
    )
    workflow.add_edge("refiner", "critic")
    workflow.add_edge("producer", END)

    return workflow


def create_app():
    """Create and compile the LangGraph app."""
    return build_graph().compile()


def generate_synopsis(
    genre: str,
    budget: int = 0,
    user_prompt: str = "",
    max_iterations: int = None,
) -> dict:
    """Run the full synopsis generation pipeline."""
    log.info(f"=== Synopsis Generation START: genre='{genre}', budget=${budget:,} ===")
    start_time = time.time()

    app = create_app()

    initial_state: GraphState = {
        "user_prompt": user_prompt,
        "genre": genre,
        "budget": budget,
        "constraints": {},
        "retrieved_examples": [],
        "synopsis": "",
        "critique": {},
        "score": 0.0,
        "budget_breakdown": {},
        "risk_score": 0.0,
        "iteration": 0,
        "max_iterations": max_iterations or MAX_ITERATIONS,
        "history": [],
        "status": "running",
        "error": "",
    }

    final_state = app.invoke(initial_state)

    if final_state.get("status") != "failed":
        final_state["status"] = "completed"

    elapsed = time.time() - start_time
    log.info(f"=== Synopsis Generation COMPLETE: "
             f"score={final_state.get('score', 0):.3f}, "
             f"iterations={final_state.get('iteration', 0)}, "
             f"time={elapsed:.1f}s ===")

    return dict(final_state)
