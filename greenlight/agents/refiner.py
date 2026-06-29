"""
Greenlight Cinema — Refiner Agent v2
=======================================
Makes targeted improvements based on critic feedback.
Preserves strengths, fixes issues, maintains word count.

Key improvements from v1:2
  - /no_think to suppress qwen3 thinking
  - Specific before/after improvement instructions
  - Maintains 400-word target
  - Preserves named characters and settings
"""

import logging
import re

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from greenlight.config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYNOPSIS_WORDS
from greenlight.agents.state import GraphState
from greenlight.agents.writer import _clean_think_tags

log = logging.getLogger("greenlight.agents.refiner")

REFINER_SYSTEM_PROMPT = """You are an expert Hollywood script doctor. Your ONLY job is to surgically alter the provided text to fix the critic's failures.

CRITICAL INSTRUCTIONS:
1. If the critic flagged a real-world celebrity, movie, or IP, you must DELETE that name entirely and replace it with a generic fictional equivalent (e.g., replace "Hugh Jackman" with "Elias Thorne"). 
2. If the critic flagged a logic or physics error, alter ONLY the specific physical action to make it scientifically possible. DO NOT treat human beings as objects or tools (e.g., a person cannot be used as an explosive or a key).
3. Keep the exact same word count and preserve all passed constraints.
4. DO NOT explain your changes. Output ONLY the corrected synopsis.

RULES:
1. FIX each issue the critic identified — address them specifically.
2. PRESERVE everything the critic praised as strengths.
3. KEEP all named characters, settings, and plot points unless replacing them with better ones.
4. MAINTAIN the same genre, tone, and setting.
5. IMPROVE vivid, cinematic language — sensory details, emotional beats.
6. ENSURE the synopsis has clear 3-act structure with escalating stakes.
7. CRITICAL FIX: You MUST explicitly integrate ALL failed constraints so that the new synopsis fully satisfies them. Weave them naturally into the plot.
8. CRITICAL: Do NOT use real-world names, celebrities, or existing film titles. Generate 100% fictional names.

CRITICAL INSTRUCTION: You MUST maintain the {word_count}-word target (at least 400 words). DO NOT shorten the synopsis from its original length. Expanding the text is encouraged to fix constraints.

OUTPUT FORMAT: First, use a <think> block to plan your changes and explicitly verify cause-and-effect physical logic to ensure you don't break continuity. (Aim for 200-400 words). Then close it with </think>.
CRITICAL: To maintain continuity, you MUST preserve the explicit [Act X Tracker] blocks before each act's prose, updating the character states (Alive/Injured/Dead) and assets if your refinements change them.
Output ONLY the improved synopsis text with its trackers. No explanations. No commentary. No other headers."""

REFINER_HUMAN_PROMPT = """GENRE: {genre}

ORIGINAL SYNOPSIS:
{synopsis}

CRITIC SCORE: {score}/1.0

FAILED CONSTRAINTS (FIX THESE):
{failed_constraints}

SUGGESTIONS TO IMPLEMENT:
{suggestions}

PASSED CONSTRAINTS (PRESERVE THESE STRENGTHS):
{passed_constraints}

Rewrite the synopsis fixing ALL failed constraints while preserving ALL passed constraints. You MUST maintain the original Protagonist name, Setting, and Core Asset unless the critic explicitly told you to change them. Remember to start with a <think> block to plan your rewrite. Go."""


def refiner_node(state: GraphState) -> dict:
    """Refiner agent — makes targeted improvements based on critique."""
    iteration = state["iteration"] + 1
    log.info(f"Refiner agent: improving synopsis (iteration {iteration})")

    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.6,
            num_predict=4000,
            num_ctx=8192,
            top_p=0.8,
        )

        critique = state.get("critique", {})
        failed_constraints = critique.get("failed_constraints", ["No specific failures noted"])
        suggestions = critique.get("suggestions", ["Improve overall quality to meet constraints"])
        passed_constraints = critique.get("passed_constraints", ["General narrative structure"])
        score = critique.get("score", 0.5)

        # Build messages
        system_msg = SystemMessage(content=REFINER_SYSTEM_PROMPT.format(
            word_count=SYNOPSIS_WORDS
        ))
        human_msg = HumanMessage(content=REFINER_HUMAN_PROMPT.format(
            genre=state["genre"],
            synopsis=state["synopsis"],
            score=f"{score:.2f}",
            failed_constraints="\n".join(f"- {i}" for i in (failed_constraints if isinstance(failed_constraints, list) else [str(failed_constraints)])),
            suggestions="\n".join(f"- {s}" for s in (suggestions if isinstance(suggestions, list) else [str(suggestions)])),
            passed_constraints="\n".join(f"- {s}" for s in (passed_constraints if isinstance(passed_constraints, list) else [str(passed_constraints)])),
        ))

        response = llm.invoke([system_msg, human_msg])
        refined = response.content.strip()

        log.warning("=== RAW REFINER RESPONSE ===")
        log.warning(refined)
        log.warning("===========================")

        # Clean out any leaked special tokens
        refined = refined.replace('<|im_end|>', '')
        refined = refined.replace('<|endoftext|>', '')
        refined = refined.replace('<|im_start|>', '')
        refined = refined.strip()

        # Safely clean up thinking tags using robust extraction
        refined = _clean_think_tags(refined)

        # Remove any headers
        lines = refined.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("**") and stripped.endswith("**"):
                continue
            if stripped.startswith("# ") or stripped.startswith("## "):
                continue
            cleaned_lines.append(line)
        refined = "\n".join(cleaned_lines).strip()

        word_count = len(refined.split())
        log.info(f"Refiner agent: produced {word_count} words (iteration {iteration})")

        return {
            "synopsis": refined,
            "iteration": iteration,
            "status": "running",
        }

    except Exception as e:
        log.error(f"Refiner agent failed: {e}")
        return {
            "iteration": iteration,
            "status": "running",
            "error": f"Refiner agent error: {str(e)}",
        }
