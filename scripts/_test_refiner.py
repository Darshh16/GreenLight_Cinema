import os
import sys

# Add parent directory to path so we can import greenlight
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from greenlight.agents.refiner import REFINER_SYSTEM_PROMPT, REFINER_HUMAN_PROMPT
from greenlight.config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYNOPSIS_WORDS
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

def test_refiner():
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.3,
        num_predict=2000,
        num_ctx=8192,
        top_p=0.8,
    )
    
    genre = "Crime"
    synopsis = "Kai stands in the rain with a .38 revolver..."
    score = 0.2
    failed_constraints = "- Fails to leverage the trending talent (suggested cast)\n- Fails to include suggested directors"
    suggestions = "- Introduce Jake Gyllenhaal as Kai to leverage high ROI talent"
    passed_constraints = "- Matches Crime genre perfectly"
    
    system_msg = SystemMessage(content=REFINER_SYSTEM_PROMPT.format(word_count=SYNOPSIS_WORDS))
    human_msg = HumanMessage(content=REFINER_HUMAN_PROMPT.format(
        genre=genre,
        synopsis=synopsis,
        score=score,
        failed_constraints=failed_constraints,
        suggestions=suggestions,
        passed_constraints=passed_constraints,
    ))
    
    print("Invoking LLM...")
    response = llm.invoke([system_msg, human_msg])
    print("RAW RESPONSE START:")
    print(repr(response.content))
    print("RAW RESPONSE END")

if __name__ == "__main__":
    test_refiner()
