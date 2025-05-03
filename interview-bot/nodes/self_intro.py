# --- START OF FILE nodes/self_intro.py ---
from models.state import InterviewState
from typing import Dict, List # Import Dict, List

# Node returns a dict with the message to add
def ask_self_intro_node(state: InterviewState) -> Dict[str, List[Dict[str, str]]]:
    """Ask the candidate for a self-introduction."""
    print("--- Executing Node: ask_self_intro_node ---")
    intro_question = (
        "To start, could you please introduce yourself? "
        "Please share a bit about your background, experience, and why you're interested in this position."
    )

    new_message = {"role": "assistant", "content": intro_question}
    print("ask_self_intro_node: Returning new message.")
    # Return dict containing ONLY the new message(s) for add_messages
    return {"messages": [new_message]}

# --- END OF FILE nodes/self_intro.py ---