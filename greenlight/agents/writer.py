"""
Greenlight Cinema — Writer Agent v2
======================================
Generates rich, commercially viable movie synopses using:
  - Market constraints from DuckDB analytics
  - Reference scripts from ChromaDB RAG
  - 3-act structure with named characters
  - 400-word target with vivid, cinematic prose

Uses Ollama (qwen3:4b) with /no_think to suppress thinking tags.
"""

import logging
import json
import re

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from greenlight.config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYNOPSIS_WORDS
from greenlight.agents.state import GraphState

def _clean_think_tags(text: str) -> str:
    """Bulletproof extraction of final output from LLM reasoning tags."""
    text_lower = text.lower()
    
    if "</think>" in text_lower:
        idx = text_lower.rfind("</think>") + len("</think>")
        text = text[idx:].strip()
    elif "<think>" in text_lower:
        # Forgot closing tag: try to split on paragraph break
        if "\n\n" in text:
            idx = text.find("\n\n")
            text = text[idx:].strip()
        else:
            text = re.sub(r'(?i)<think>', '', text).strip()
            
    # Aggressively strip any leaked thought process headers
    # The prompt forces the story to begin with [Setting: or [Assets:
    if "[Setting:" in text:
        idx = text.find("[Setting:")
        text = text[idx:].strip()
        
    return text.strip()

log = logging.getLogger("greenlight.agents.writer")

WRITER_SYSTEM_PROMPT = """You are a veteran Hollywood screenwriter with 20 years of experience crafting commercially successful films. You write vivid, cinematic movie synopses that studios greenlight.

STRICT RULES:
1. Write a {word_count}-word synopsis (minimum 300 words, maximum 500 words).
2. Use a clear 3-ACT STRUCTURE:
   - ACT 1 (Setup): Introduce the protagonist by NAME, their world, and the inciting incident.
   - ACT 2 (Confrontation): Escalate conflict, introduce antagonist, raise stakes.
   - ACT 3 (Resolution): Climax, character transformation, and a compelling ending.
3. USE THE REFERENCE SCREENPLAYS FOR TONE AND PACING ONLY. Analyze how they build tension and format descriptions, but ABSOLUTELY DO NOT copy their character names, locations, or specific plot elements. Your characters must be 100% original.
4. Write with CINEMATIC energy — show, don't tell. Borrow the pacing, gritty tone, and specific sensory details directly from the reference excerpts.
5. The tone and scope MUST match the genre and budget tier.
6. End with a hook that makes the reader desperate to see this film.
7. Merge the borrowed elements into a new, original storyline based on the user prompt.
8. ENSURE FLAWLESS LOGIC & CAUSALITY: The narrative must be logically sound from start to finish. Actions in Act 1 must have strict logical consequences in Act 2 and 3. Characters CANNOT be killed or fatally injured in one act and reappear perfectly fine in the next. CRITICAL RULE FOR RESOLUTIONS: If the protagonist defeats the antagonist or makes a sacrifice, it MUST make strict logical and real-world sense. Do NOT have characters defeat villains by simply handing them exactly what they want based on empty verbal promises. In corporate or grounded settings, victories must use actual leverage, legal traps, or realistic strategy.
9. SPATIAL & WARDROBE CONTINUITY: Keep precise track of character location, clothing, and environment. Characters cannot teleport between locations (e.g., from an indoor boardroom to a street) without transition, nor can they wear soaking wet raincoats during professional indoor meetings. DO NOT treat human beings as inanimate objects or tools (e.g., a person is not a key or thermal spike).
10. INVENTORY CONTINUITY: Do NOT introduce magical MacGuffins or sudden crucial tools (e.g., a "quantum key") in Act 2 or 3. If a character uses an object to solve the climax, it MUST be introduced in Act 1 and explicitly listed in your Setting and Asset Tracker.
11. ENVIRONMENTAL CONTINUITY: Maintain strict atmospheric consistency. Do not contradict the immediate setting within adjacent sentences (e.g., do not state "the rain stops" and then immediately say "he stands alone in the rain").
12. NO POWER CREEP: If a character has a specific ability or skill, they must use THAT specific ability to solve problems. Do not escalate into generic superhero tropes (e.g., suddenly turning into a glowing energy vortex) at the climax. Keep the stakes and abilities grounded.
13. CRITICAL MARKET CONSTRAINTS: You MUST strictly integrate ALL provided MARKET CONSTRAINTS (e.g. seasonal release windows, trending talent archetypes, themes). Explicitly weave these elements into the story. Failure to include them will result in immediate rejection.
14. CRITICAL: Do NOT use real-world names, celebrities, or existing film titles. Generate 100% fictional names.

OUTPUT FORMAT: First, use a <think> block to explicitly verify cause-and-effect physical logic across all 3 acts. Map out character states (alive/dead/injured) for each act. (Aim for 200-400 words). Then close it with </think> and write the synopsis.
CRITICAL: To maintain continuity, you MUST start EACH of the 3 Acts with an explicit tracker before the prose. 
Example:
[Act 1 Tracker]
Setting: NYC Penthouse
Characters: Kai (Alive, unhurt), Leo (Alive, unhurt)
Assets: .38 Revolver (loaded)
[End Tracker]
(Act 1 prose goes here...)
[Act 2 Tracker] ... etc.
Do not use other headers. Do not use meta-commentary."""

WRITER_HUMAN_PROMPT = """GENRE: {genre}
BUDGET TIER: {budget_tier}

USER CREATIVE PROMPT / IDEA:
{user_prompt}

MARKET CONSTRAINTS:
{constraints}

REFERENCE SCREENPLAYS FOR INSPIRATION (Use these for tone, pacing, and style references):
{examples}

Write a vivid, compelling {word_count}-word {genre} movie synopsis now. Remember: named characters, specific settings, 3-act structure, cinematic prose. Go."""


def writer_node(state: GraphState) -> dict:
    """Writer agent — generates a rich, 400-word synopsis."""
    log.info(f"Writer agent: generating {state['genre']} synopsis (iteration {state['iteration']})")

    try:
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3,
            num_predict=4000,
            num_ctx=8192,
            top_p=0.85,
        )

        # Format constraints
        constraints_text = state.get("constraints", {})
        if isinstance(constraints_text, dict):
            if "prompt_text" in constraints_text:
                constraints_text = constraints_text["prompt_text"]
            else:
                constraints_text = json.dumps(constraints_text, indent=2)

        # Format budget tier
        budget = state.get("budget", 0)
        if budget >= 100_000_000:
            budget_tier = "Blockbuster ($100M+)"
        elif budget >= 50_000_000:
            budget_tier = "High Budget ($50-100M)"
        elif budget >= 15_000_000:
            budget_tier = "Mid Budget ($15-50M)"
        elif budget > 0:
            budget_tier = "Low Budget (under $15M)"
        else:
            budget_tier = "Mid Budget"

        # Format retrieved examples — now real screenplay excerpts
        examples = state.get("retrieved_examples", [])
        if examples:
            examples_text = ""
            for i, ex in enumerate(examples[:2]):
                if isinstance(ex, dict):
                    title = ex.get("title", ex.get("source", "Unknown"))
                    genre = ex.get("genre", "")
                    year = ex.get("year", "")
                    act = ex.get("act", "")
                    doc = ex.get("document", str(ex))
                    header = f"--- Screenplay Excerpt {i+1}: {title}"
                    if genre:
                        header += f" ({genre}"
                        if year:
                            header += f", {year}"
                        header += ")"
                    if act:
                        header += f" [{act.replace('_', ' ').title()}]"
                    header += " ---"
                    examples_text += f"\n{header}\n{doc}\n"
                else:
                    examples_text += f"\n--- Screenplay Excerpt {i+1} ---\n{ex}\n"
        else:
            examples_text = "(No reference screenplays available — be creative!)"

        # Build messages
        system_msg = SystemMessage(content=WRITER_SYSTEM_PROMPT.format(
            word_count=SYNOPSIS_WORDS
        ))
        human_msg = HumanMessage(content=WRITER_HUMAN_PROMPT.format(
            genre=state["genre"],
            budget_tier=budget_tier,
            user_prompt=state.get("user_prompt", "(No specific prompt provided. Use your imagination.)"),
            constraints=constraints_text,
            examples=examples_text,
            word_count=SYNOPSIS_WORDS,
        ))

        response = llm.invoke([system_msg, human_msg])
        synopsis = response.content.strip()
        
        log.warning("=== RAW WRITER RESPONSE ===")
        log.warning(synopsis)
        log.warning("===========================")

        # Clean out any leaked special tokens that could break downstream agents
        synopsis = synopsis.replace('<|im_end|>', '')
        synopsis = synopsis.replace('<|endoftext|>', '')
        synopsis = synopsis.replace('<|im_start|>', '')
        synopsis = synopsis.strip()

        # Safely clean up thinking tags using robust extraction
        synopsis = _clean_think_tags(synopsis)

        # Remove any headers/titles the model might add
        lines = synopsis.split("\n")
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip header-like lines
            if stripped.startswith("**") and stripped.endswith("**"):
                continue
            if stripped.startswith("# ") or stripped.startswith("## "):
                continue
            if stripped.upper() == stripped and len(stripped) < 50 and ":" not in stripped:
                continue  # All-caps title line
            cleaned_lines.append(line)
        synopsis = "\n".join(cleaned_lines).strip()

        word_count = len(synopsis.split())
        log.info(f"Writer agent: generated {word_count} words")

        return {
            "synopsis": synopsis,
            "iteration": state["iteration"],
            "status": "running",
        }

    except Exception as e:
        log.error(f"Writer agent failed: {e}")
        return {
            "synopsis": "",
            "status": "failed",
            "error": f"Writer agent error: {str(e)}",
        }
