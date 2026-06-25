import os
import sys

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOllama(
    model="qwen3:4b",
    base_url="http://localhost:11434",
    temperature=0.4,
    format="json",
    num_ctx=8192,
    top_p=0.9,
)

CRITIC_SYSTEM_PROMPT = """You are a senior Hollywood script evaluator and market analyst. You evaluate movie synopses to ensure they meet strict market constraints.

EVALUATION CRITERIA:
1. Does the synopsis clearly belong to the requested genre?
2. Does it align with the seasonal release ROI trends (e.g., if summer blockbusters are needed, does it feel like a summer blockbuster)?
3. Does it leverage the trending talent or character archetypes suggested in the constraints?
4. Is the narrative compelling (3-act structure, named characters) AND logically sound? Are there any plot holes, confusing leaps in logic, or unmotivated character actions?

SCORING RULES (0.0 to 1.0):
- 0.9-1.0: Meets all constraints perfectly, highly commercial.
- 0.7-0.8: Good story, meets most constraints.
- 0.5-0.6: Meets some constraints but ignores others.
- 0.0-0.4: Fails to meet core constraints.

REQUIRED JSON SCHEMA:
You MUST output exactly 4 keys: "score", "passed_constraints", "failed_constraints", and "suggestions". DO NOT output a "reason" key.

OUTPUT ONLY VALID JSON WITH EXACTLY THESE 4 KEYS. Do not include any other text."""

CRITIC_HUMAN_PROMPT = """Evaluate this Romance movie synopsis.

MARKET CONSTRAINTS:
{"prompt_text": "Must include a rainy kiss scene. Must feature a career-focused female lead. Must align with Q4 holiday release themes."}

SYNOPSIS (405 words):
Sarah is a brilliant but overworked architect living in Seattle. She has just been handed the most important project of her career: designing the city's new central library. John is a free-spirited landscape designer who has been hired to create the outdoor green spaces for the same library. From their first meeting, they clash. Sarah is all about sharp lines, modern aesthetics, and rigid schedules. John believes in organic flow, natural curves, and taking his time. Their bickering becomes the talk of the office.

As the project progresses, however, they are forced to spend long hours together. One late evening, while reviewing blueprints, the power goes out. With nothing to do but talk by the light of their cell phones, they discover they have more in common than they thought. Sarah learns about John's passion for native plants and his dream of creating a sustainable community garden. John learns about Sarah's childhood dream of building a home that felt safe and welcoming, a stark contrast to her chaotic upbringing.

The turning point comes when a severe storm threatens to delay the project. They have to rush to the construction site to secure the materials. Working side-by-side in the pouring rain and howling wind, they manage to save the critical supplies. Soaked to the bone and freezing, they take shelter in a nearby coffee shop. As they huddle over warm mugs of coffee, the tension between them shifts from frustration to undeniable attraction. 

Despite their growing feelings, professional boundaries keep them apart. Sarah is up for a major promotion, and any hint of a workplace romance could jeopardize her chances. John, sensing her hesitation, pulls back, focusing entirely on his work. The library's grand opening is a massive success. Sarah gets her promotion, and John's landscape design is universally praised. But as Sarah looks out over the beautiful gardens John created, she realizes the promotion feels empty without him. 

In a dramatic, last-minute decision, she leaves the celebratory gala and searches for John. She finds him in the very community garden he had dreamed of building, which he has just finished. Standing under the stars, she confesses her feelings. John smiles, pulling her into a kiss. They agree to start their own design firm together, blending her structure with his organic flow, building a life and a business side by side.

Provide your evaluation below as a JSON object:"""

print("Running pure ChatOllama test...")
try:
    response = llm.invoke([SystemMessage(content=CRITIC_SYSTEM_PROMPT), HumanMessage(content=CRITIC_HUMAN_PROMPT)])
    print("RESPONSE:")
    print(repr(response.content))
except Exception as e:
    print("FAILED:", e)
