# --- START OF FILE nodes/extract_info.py ---
import json
from models.state import InterviewState
from utils.llm import get_openrouter_completion, format_messages_for_openrouter
from typing import Dict, Any
import traceback
from langchain_core.messages import BaseMessage

# Node returns dict of updates for non-message fields
def extract_info_node(state: InterviewState) -> Dict[str, Any]:
    """
    Extract candidate information from their self-introduction.
    Handles BaseMessage objects in state.messages.
    Returns a dictionary containing 'candidate_name' and 'candidate_background'.
    """
    print("--- Executing Node: extract_info_node ---")

    if not state.messages:
         print("extract_info_node: Message list is empty.")
         return {}

    last_message = state.messages[-1]
    is_user_message = False
    candidate_response = ""
    if isinstance(last_message, BaseMessage) and last_message.type == 'human':
        is_user_message = True
        candidate_response = last_message.content
    elif isinstance(last_message, dict) and last_message.get("role") == "user":
        is_user_message = True
        candidate_response = last_message.get("content", "")
        print("Warning: Found dict message in state, expected BaseMessage.")

    if not is_user_message:
        print("extract_info_node: Last message is not from user.")
        return {}

    print(f"extract_info_node: Processing user response: '{candidate_response[:100]}...'")

    # --- Improved System Prompt ---
    system_prompt = """
    You are an expert AI recruiter. Extract key information from a candidate's self-introduction.
    Your goal is to populate a JSON object with the following structure:
    ```json
    {
        "candidate_name": "Extracted name or 'Candidate' if not found",
        "candidate_background": "A detailed summary of the candidate's background, experience, skills, and interests based *only* on the provided introduction."
    }
    ```
    Focus ONLY on the introduction provided. Keep the background concise but capture key points mentioned.
    **IMPORTANT: Respond with ONLY the JSON object specified above, enclosed in triple backticks. Do NOT include ANY introductory text, concluding remarks, explanations, or any other text outside the JSON structure.**
    """
    # --- End Improved System Prompt ---

    messages_for_llm = format_messages_for_openrouter(
        system_message=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Here is the candidate's self-introduction:\n\n{candidate_response}"
        }]
    )
            # Asking the AI & Getting the Answer:


    update_dict = {}
    extracted_info = None # Initialize
    try:
        completion = get_openrouter_completion(messages_for_llm)
        print(f"extract_info_node: LLM completion received: {completion}")

        # --- Robust JSON Parsing ---

# Trying to Understand the AI's Answer (JSON Parsing):

        try:
            # Attempt 1: Find JSON within potential backticks or direct output
            json_part = completion
            if '```json' in completion:
                start_idx = completion.find('{')
                end_idx = completion.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_part = completion[start_idx:end_idx]
            elif completion.strip().startswith('{') and completion.strip().endswith('}'):
                 json_part = completion.strip() # Assume it's just the JSON
            else:
                 # Fallback: find first { and last } if no clear markers
                 start_idx = completion.find('{')
                 end_idx = completion.rfind('}') + 1
                 if start_idx != -1 and end_idx != -1:
                     json_part = completion[start_idx:end_idx]

            extracted_info = json.loads(json_part)
            print(f"extract_info_node: Successfully parsed JSON: {extracted_info}")

        except json.JSONDecodeError as json_e:
             print(f"extract_info_node: JSONDecodeError - {json_e}. Raw completion: {completion}")
             extracted_info = None # Parsing failed
        except Exception as parse_e:
             print(f"extract_info_node: General parsing error - {parse_e}. Raw completion: {completion}")
             extracted_info = None # Parsing failed
        # --- End Robust JSON Parsing ---

        # Populate update_dict based on parsing success
        if extracted_info and isinstance(extracted_info, dict):
            update_dict = {
                "candidate_name": extracted_info.get("candidate_name", "Candidate").strip(),
                "candidate_background": extracted_info.get("candidate_background", "").strip()
            }
        else: # Parsing failed, use fallback
            print("extract_info_node: Using fallback due to parsing failure.")
            update_dict = {
                "candidate_name": "Candidate",
                "candidate_background": f"Could not parse details. Raw intro: {candidate_response[:500]}"
            }

    except Exception as e:
        print(f"extract_info_node: Error calling LLM or processing: {e}")
        traceback.print_exc()
        # Fallback dict on LLM error
        update_dict = {
            "candidate_name": "Candidate",
            "candidate_background": candidate_response[:500]
        }

    print(f"extract_info_node: Returning updates: {update_dict}")
    return update_dict
# --- END OF FILE nodes/extract_info.py ---