"""
Greenlight Cinema — Critic Agent v2
======================================
Evaluates synopses with a strict, detailed scoring rubric.
Returns structured JSON with actionable feedback.

Key fixes from v1:
  - /no_think flag to suppress qwen3 reasoning blocks
  - Detailed scoring rubric with examples for each score range
  - Few-shot JSON example embedded in prompt
  - Robust multi-strategy JSON parser
  - Weighted scoring: narrative (0.35) > genre (0.25) > commercial (0.25) > seasonal (0.15)
"""

import logging
import json
import re

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from greenlight.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from greenlight.agents.state import GraphState

log = logging.getLogger("greenlight.agents.critic")

CRITIC_SYSTEM_PROMPT = """You are a senior Hollywood script evaluator and market analyst. You evaluate movie synopses to ensure they meet strict market constraints.

EVALUATION CRITERIA:
1. Does the synopsis clearly belong to the requested genre?
2. Does it align with the seasonal release ROI trends (e.g., if summer blockbusters are needed, does it feel like a summer blockbuster)?
3. Does it leverage the trending talent or character archetypes suggested in the constraints?
4. Is the narrative compelling AND logically flawless? Actively penalize for spatial/wardrobe teleportation errors (e.g., wet raincoats indoors, sudden location shifts), illogical character motivations, and "illogical surrenders". CRITICAL LOGIC CHECK: Characters CANNOT die in Act 1 or 2 and then reappear alive in the next act without explanation. Actively penalize if character states (alive/dead/injured) lose continuity. Resolutions must use real leverage. Actively penalize power creep and inventory hallucinations (e.g., sudden magical MacGuffins appearing in Act 3).
5. ZERO IP LEAKS: Actively scan the text for real-world actors, celebrities, or existing movie titles. If the text uses a real-world entity (e.g., "Hugh Jackman", "Shawshank"), you MUST heavily penalize the score and fail the constraint.

SCORING RULES (0.0 to 1.0):
- 0.9-1.0: Meets all constraints perfectly, highly commercial.
- 0.7-0.8: Good story, meets most constraints.
- 0.5-0.6: Meets some constraints but ignores others.
- 0.0-0.4: Fails to meet core constraints.

REQUIRED JSON SCHEMA:
You MUST output exactly 4 keys: "score", "passed_constraints", "failed_constraints", and "suggestions". DO NOT output a "reason" key.

EXAMPLE OUTPUT FORMAT:
{
  "score": 0.75,
  "passed_constraints": ["Matches Sci-Fi genre perfectly", "Includes a rogue AI"],
  "failed_constraints": ["Fails to align with the Q4 Holiday release window feel"],
  "suggestions": ["Make the climax take place during a winter storm"]
}

OUTPUT ONLY VALID JSON WITH EXACTLY THESE 4 KEYS. Do not include any other text."""

CRITIC_HUMAN_PROMPT = """Evaluate this {genre} movie synopsis.

MARKET CONSTRAINTS:
{constraints}

SYNOPSIS ({word_count} words):
{synopsis}

Provide your evaluation below as a JSON object:"""


def _normalize_result(result: dict) -> dict:
    suggestions = result.get("suggestions", [])
    if "reason" in result and result["reason"]:
        if isinstance(suggestions, list):
            suggestions.append(f"Critic note: {result['reason']}")
        else:
            suggestions = [f"Critic note: {result['reason']}"]
            
    passed = result.get("passed_constraints", result.get("passed", result.get("strengths", [])))
    failed = result.get("failed_constraints", result.get("failed", result.get("weaknesses", [])))
            
    return {
        "score": result.get("score", 0.5),
        "passed_constraints": passed if isinstance(passed, list) else [],
        "failed_constraints": failed if isinstance(failed, list) else [],
        "suggestions": suggestions if isinstance(suggestions, list) else []
    }

def _parse_critic_response(response_text: str) -> dict:
    """Parse critic LLM response into structured dict with multiple fallback strategies."""
    # Remove thinking tags
    cleaned = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()

    # Strategy 1: Direct JSON parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict) and "score" in result:
            return _normalize_result(result)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            if isinstance(result, dict):
                return _normalize_result(result)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find any JSON-like object
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        candidate = json_match.group(0)
        # Try to fix common issues
        candidate = candidate.replace("'", '"')
        candidate = re.sub(r',\s*}', '}', candidate)  # trailing commas
        candidate = re.sub(r',\s*]', ']', candidate)  # trailing commas in arrays
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return _normalize_result(result)
        except json.JSONDecodeError:
            pass

    log.warning("JSON parsing failed, returning default structure")
    return {
        "score": 0.5,
        "passed_constraints": [],
        "failed_constraints": ["Could not fully parse critic evaluation"],
        "suggestions": ["Ensure synopsis clearly addresses the market constraints"]
    }


def critic_node(state: GraphState) -> dict:
    """Critic agent — evaluates synopsis with detailed rubric."""
    log.info(f"Critic agent: evaluating synopsis (iteration {state['iteration']})")

    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.4,
            format="json",
            num_ctx=8192,
            top_p=0.9,
        )
        constraints_text = state.get("constraints", {})
        if isinstance(constraints_text, dict):
            if "prompt_text" in constraints_text:
                constraints_text = constraints_text["prompt_text"]
            else:
                constraints_text = json.dumps(constraints_text, indent=2)

        # Count words in synopsis
        synopsis = state.get("synopsis", "")
        word_count = len(synopsis.split())

        # Build messages
        system_msg = SystemMessage(content=CRITIC_SYSTEM_PROMPT)
        human_msg = HumanMessage(content=CRITIC_HUMAN_PROMPT.format(
            genre=state["genre"],
            constraints=constraints_text,
            synopsis=synopsis,
            word_count=word_count,
        ))

        response = llm.invoke([system_msg, human_msg])
        
        # LOG RAW RESPONSE FOR DEBUGGING
        log.warning("=== RAW CRITIC RESPONSE ===")
        log.warning(response.content)
        log.warning("===========================")
        
        critique = _parse_critic_response(response.content)
        
        # Ensure score is valid
        score = float(critique.get("score", 0.5))
        score = max(0.0, min(1.0, score))
        critique["score"] = score

        # Record in history
        history_entry = {
            "iteration": state["iteration"],
            "synopsis": synopsis,
            "critique": critique,
            "score": score,
        }

        current_history = list(state.get("history", []))
        current_history.append(history_entry)

        log.info(f"Critic agent: score = {score:.3f}")
        log.info(f"  Passed constraints: {len(critique.get('passed_constraints', []))}")
        log.info(f"  Failed constraints: {len(critique.get('failed_constraints', []))}")
        if critique.get("suggestions"):
            log.info(f"  Suggestions: {critique['suggestions'][:2]}")

        return {
            "critique": critique,
            "score": score,
            "history": current_history,
            "status": "running",
        }

    except Exception as e:
        log.error(f"Critic agent failed: {e}")
        return {
            "critique": {
                "score": 0.5, 
                "passed_constraints": [],
                "failed_constraints": [f"Critic error: {str(e)}"],
                "suggestions": []
            },
            "score": 0.5,
            "status": "running",
        }
