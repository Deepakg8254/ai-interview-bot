# --- START OF FILE nodes/company_intro.py ---
from models.state import InterviewState
from config import COMPANY_NAME, COMPANY_DESCRIPTION, COMPANY_ROLE
from typing import Dict, List # Import Dict, List

# Node returns a dict with the message to add
def company_intro_node(state: InterviewState) -> Dict[str, List[Dict[str, str]]]:
    """Initialize the interview with a company introduction."""
    print("--- Executing Node: company_intro_node ---")
    intro_message = (
        f"Welcome to your interview with {COMPANY_NAME}. "
        f"I'll be conducting your interview for the {COMPANY_ROLE} position today. "
        f"\n\n{COMPANY_DESCRIPTION}\n\n"
        f"This interview will consist of several questions to assess your skills and fit for the role. "
        f"Let's begin, shall we?"
    )

    new_message = {"role": "assistant", "content": intro_message}
    print("company_intro_node: Returning new message.")
    # Return dict containing ONLY the new message(s) for add_messages
    return {"messages": [new_message]}

# --- END OF FILE nodes/company_intro.py ---