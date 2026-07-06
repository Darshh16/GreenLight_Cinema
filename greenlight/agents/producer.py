"""
Greenlight Cinema — Producer Agent
====================================
Evaluates the final synopsis against market constraints
to generate a mock budget breakdown and risk score.
"""

import logging
import json
import re

from langchain_core.messages import SystemMessage, HumanMessage

from greenlight.config import get_llm
from greenlight.agents.state import GraphState

log = logging.getLogger("greenlight.agents.producer")

PRODUCER_SYSTEM_PROMPT = """You are an expert Hollywood Line Producer and Studio Risk Assessor.
Your job is to read a finalized movie synopsis and its target market constraints, and output a budget breakdown and a Greenlight Risk Score.

CRITICAL INSTRUCTIONS:
1. Estimate a rough percentage breakdown of the budget across 4 categories: "Talent", "VFX & Production", "Locations & Sets", and "Marketing". They MUST sum to exactly 100.
2. Evaluate the "Risk Score" (0.0 to 1.0) where 0.0 is completely safe (guaranteed hit) and 1.0 is extremely risky (likely to bomb). Take into account the genre, budget tier, and whether the story seems too niche or too expensive to pull off.
3. OUTPUT FORMAT: First, use a <think> block to justify your budget allocation and risk assessment. Keep your <think> block concise (under 50 words). Then, close the block with </think>. Finally, output EXACTLY ONE valid JSON block formatted like this:
```json
{
  "budget_breakdown": {
    "Talent": 30,
    "VFX & Production": 40,
    "Locations & Sets": 10,
    "Marketing": 20
  },
  "risk_score": 0.45
}
```
Do NOT output anything else after the JSON.
"""

PRODUCER_HUMAN_PROMPT = """GENRE: {genre}
BUDGET TIER: {budget_tier}

SYNOPSIS:
{synopsis}

CONSTRAINTS:
{constraints}

Provide the budget breakdown and risk score JSON now:"""

def producer_node(state: GraphState) -> dict:
    """Producer agent — generates budget breakdown and risk score."""
    if state.get("status") == "failed":
        return {}
        
    log.info(f"Producer agent: evaluating final synopsis")

    try:
        llm = get_llm(temperature=0.4)

        constraints_str = json.dumps(state.get("constraints", {}), indent=2)
        budget_tier = state.get("constraints", {}).get("target_budget_tier", "Unknown")

        system_msg = SystemMessage(content=PRODUCER_SYSTEM_PROMPT)
        human_msg = HumanMessage(content=PRODUCER_HUMAN_PROMPT.format(
            genre=state.get("genre", ""),
            budget_tier=budget_tier,
            synopsis=state.get("synopsis", ""),
            constraints=constraints_str
        ))

        response = llm.invoke([system_msg, human_msg])
        content = response.content.strip()

        # Extract JSON from the output
        json_str = "{}"
        if "```json" in content:
            parts = content.split("```json")
            if len(parts) > 1:
                json_part = parts[1].split("```")[0]
                json_str = json_part.strip()
        elif "```" in content:
            parts = content.split("```")
            for p in parts:
                if "{" in p and "}" in p:
                    json_str = p.strip()
                    break
        else:
            # Fallback regex to find a JSON block
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                json_str = match.group(0)

        try:
            parsed = json.loads(json_str)
            budget_breakdown = parsed.get("budget_breakdown", {"Talent": 25, "VFX & Production": 45, "Locations & Sets": 15, "Marketing": 15})
            risk_score = float(parsed.get("risk_score", 0.5))
        except json.JSONDecodeError:
            log.warning("Producer failed to output valid JSON, using defaults.")
            budget_breakdown = {"Talent": 25, "VFX & Production": 45, "Locations & Sets": 15, "Marketing": 15}
            risk_score = 0.5

        log.info(f"Producer agent: Risk Score = {risk_score:.2f}")

        return {
            "budget_breakdown": budget_breakdown,
            "risk_score": risk_score,
            "status": "completed", # Because this is the last step
        }

    except Exception as e:
        log.error(f"Producer agent failed: {e}")
        return {
            "budget_breakdown": {"Talent": 25, "VFX & Production": 45, "Locations & Sets": 15, "Marketing": 15},
            "risk_score": 0.5,
            "status": "completed",
            "error": f"Producer agent error: {str(e)}",
        }
