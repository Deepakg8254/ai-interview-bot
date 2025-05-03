# --- START OF FILE nodes/analysis.py ---
import json
from models.state import InterviewState
from utils.llm import get_openrouter_completion, format_messages_for_openrouter
from typing import Dict, Any
import traceback
from langchain_core.messages import BaseMessage

# Node returns dict of updates for non-message fields
def analyze_answer_node(state: InterviewState) -> Dict[str, Any]:  
    #  return a dictionary containing the updates it wants to make to the interview state (like adding the analysis results).
    """
    Analyze the candidate's answer. Handles BaseMessage objects.
    Returns dict with 'answers', 'answer_analyses', 'current_question_index', 'interview_complete'.
    """
    print("--- Executing Node: analyze_answer_node ---")

    if not state.interview_questions or state.current_question_index >= len(state.interview_questions):
        if state.interview_questions and state.current_question_index >= len(state.interview_questions) and not state.interview_complete:
             return {"interview_complete": True}
        return {}
    # Checks if there are actually questions generated and if we haven't already gone past the last question index or not?

    current_question = state.interview_questions[state.current_question_index]

    if not state.messages: return {}
    last_message = state.messages[-1]
    # Gets the very last message added to the conversation history (this should be the candidate's answer).
    is_user_answer = False
    candidate_answer = ""
    if isinstance(last_message, BaseMessage) and last_message.type == 'human':
        is_user_answer = True
        candidate_answer = last_message.content
    elif isinstance(last_message, dict) and last_message.get("role") == "user":
        is_user_answer = True
        candidate_answer = last_message.get("content", "")

    if not is_user_answer:
        print("analyze_answer_node: Last message is not from user.")
        return {}

    print(f"analyze_answer_node: Analyzing Q{state.current_question_index}: '{current_question}' A: '{candidate_answer[:100]}...'")

    # --- Improved System Prompt ---
    system_prompt = """
    You are an expert technical interviewer. Analyze the candidate's answer to the given question based on clarity, technical accuracy, relevance, and communication.
    Provide ONLY a JSON object with the following structure, enclosed in triple backticks:
    ```json
    {
        "strengths": ["list", "of", "key", "strengths", "observed"],
        "weaknesses": ["list", "of", "key", "weaknesses", "or", "areas", "for", "improvement"],
        "relevance_score": 0-10 (integer, how relevant was the answer to the question?),
        "technical_accuracy": 0-10 (integer, how technically correct was the answer?),
        "communication_score": 0-10 (integer, how clearly was the answer communicated?),
        "overall_score": 0-10 (integer, overall quality considering all factors),
        "brief_analysis": "A brief text analysis (1-2 concise sentences) summarizing the answer's quality."
    }
    ```
    **IMPORTANT: Rate strictly from 0 to 10. Be objective. Output ONLY the JSON object within triple backticks. Do NOT include ANY other text, commentary, greetings, explanations, or markdown formatting outside the JSON structure.**
    """
    # --- End Improved System Prompt ---

    messages_for_llm = format_messages_for_openrouter(
        system_message=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Question: {current_question}\n\nCandidate's Answer:\n```\n{candidate_answer}\n```"
        }]
    )

    # Prepares the complete prompt (system instructions + user message containing the question and the candidate's answer) 
    # in the format required by the OpenRouter API.

    analysis = {}
    analysis_parsed = False # Flag to track parsing success
    try:
        completion = get_openrouter_completion(messages_for_llm)
        print(f"analyze_answer_node: LLM completion received: {completion}")

        # --- Robust JSON Parsing ---
        try:
            json_part = completion # Start with full completion
            # Try finding markers first
            if '```json' in completion:
                start_idx = completion.find('{')
                end_idx = completion.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_part = completion[start_idx:end_idx]
            elif completion.strip().startswith('{') and completion.strip().endswith('}'):
                 json_part = completion.strip()
            else: # Fallback find brackets
                 start_idx = completion.find('{')
                 end_idx = completion.rfind('}') + 1
                 if start_idx != -1 and end_idx != -1:
                     json_part = completion[start_idx:end_idx]

            analysis = json.loads(json_part)

            # Basic validation of structure
            required_keys = ["strengths", "weaknesses", "relevance_score", "technical_accuracy", "communication_score", "overall_score", "brief_analysis"]
            if not all(key in analysis for key in required_keys):
                 print("Warning: LLM analysis response missing required keys.")
                 raise ValueError("Missing keys in analysis JSON")

            print(f"analyze_answer_node: Successfully parsed JSON analysis: {analysis}")
            analysis_parsed = True # Set flag

        except Exception as parse_e:
            print(f"analyze_answer_node: Error parsing analysis JSON ({parse_e}). Raw: {completion}")
            # Fallback analysis remains below
        # --- End Robust JSON Parsing ---

    except Exception as e:
        print(f"analyze_answer_node: Error calling LLM for analysis: {e}")
        traceback.print_exc()
        # Fallback analysis remains below

    # Use fallback if parsing failed
    if not analysis_parsed:
        print("analyze_answer_node: Using fallback analysis due to parsing/LLM error.")
        analysis = {
            "strengths": [], "weaknesses": ["Analysis Error"],
            "relevance_score": 3, "technical_accuracy": 3, "communication_score": 3, "overall_score": 3,
            "brief_analysis": "Could not automatically analyze the answer."
        }

    # Prepare updates dictionary for non-message fields
    # Ensure lists exist before appending (should be handled by Pydantic default_factory)
    new_analyses = state.answer_analyses + [analysis]
    new_answers = state.answers + [candidate_answer] # Store raw answer string
    next_question_index = state.current_question_index + 1
    is_complete = next_question_index >= len(state.interview_questions)

    update_dict = {
        "answer_analyses": new_analyses,
        "answers": new_answers,
        "current_question_index": next_question_index,
        "interview_complete": is_complete
    }
    print(f"analyze_answer_node: Returning updates: {update_dict}")
    return update_dict
# --- END OF FILE nodes/analysis.py ---