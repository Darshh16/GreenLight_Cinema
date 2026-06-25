import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from greenlight.agents.core import critic_node, GraphState

long_synopsis = """Sarah is a brilliant but overworked architect living in Seattle. She has just been handed the most important project of her career: designing the city's new central library. John is a free-spirited landscape designer who has been hired to create the outdoor green spaces for the same library. From their first meeting, they clash. Sarah is all about sharp lines, modern aesthetics, and rigid schedules. John believes in organic flow, natural curves, and taking his time. Their bickering becomes the talk of the office.

As the project progresses, however, they are forced to spend long hours together. One late evening, while reviewing blueprints, the power goes out. With nothing to do but talk by the light of their cell phones, they discover they have more in common than they thought. Sarah learns about John's passion for native plants and his dream of creating a sustainable community garden. John learns about Sarah's childhood dream of building a home that felt safe and welcoming, a stark contrast to her chaotic upbringing.

The turning point comes when a severe storm threatens to delay the project. They have to rush to the construction site to secure the materials. Working side-by-side in the pouring rain and howling wind, they manage to save the critical supplies. Soaked to the bone and freezing, they take shelter in a nearby coffee shop. As they huddle over warm mugs of coffee, the tension between them shifts from frustration to undeniable attraction. 

Despite their growing feelings, professional boundaries keep them apart. Sarah is up for a major promotion, and any hint of a workplace romance could jeopardize her chances. John, sensing her hesitation, pulls back, focusing entirely on his work. The library's grand opening is a massive success. Sarah gets her promotion, and John's landscape design is universally praised. But as Sarah looks out over the beautiful gardens John created, she realizes the promotion feels empty without him. 

In a dramatic, last-minute decision, she leaves the celebratory gala and searches for John. She finds him in the very community garden he had dreamed of building, which he has just finished. Standing under the stars, she confesses her feelings. John smiles, pulling her into a kiss. They agree to start their own design firm together, blending her structure with his organic flow, building a life and a business side by side."""

test_state = GraphState(
    genre="Romance",
    budget=100_000_000,
    user_prompt="A story about two people falling in love.",
    constraints={"prompt_text": "Must include a rainy kiss scene. Must feature a career-focused female lead. Must align with Q4 holiday release themes."},
    retrieved_examples=[],
    synopsis=long_synopsis,
    critique={},
    score=0.0,
    iteration=1,
    max_iterations=3,
    history=[],
    status="running",
    error=""
)

print("Testing critic node...")
result = critic_node(test_state)
print("Critic result:", result)
