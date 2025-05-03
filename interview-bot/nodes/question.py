# --- START OF FILE nodes/question.py ---
from models.state import InterviewState
from utils.llm import get_openrouter_completion, format_messages_for_openrouter
from config import NUM_INTERVIEW_QUESTIONS, COMPANY_ROLE
from typing import Dict, Any, List # Add List import
import traceback
import ast

# Node returns dict of updates for non-message fields
def generate_questions_node(state: InterviewState) -> Dict[str, Any]:
    """
    Generate interview questions based on candidate's background.
    Returns a dictionary containing 'interview_questions'.
    """
    print("--- Executing Node: generate_questions_node ---")

    default_questions = [
        "Can you describe your most challenging project and how you approached it?",
        "What programming languages and frameworks are you most comfortable with?",
        "How do you handle tight deadlines and pressure?",
        "Tell me about a time you had to learn a new technology quickly.",
        "How do you approach debugging a complex issue?",
        "What's your experience with version control systems like Git?",
        "Describe your understanding of object-oriented programming principles.",
        "What are your long-term career goals?"
    ] # Ensure enough defaults

    if not state.candidate_background:
        print("generate_questions_node: No background info, using default questions.")
        questions = default_questions[:NUM_INTERVIEW_QUESTIONS]
        return {"interview_questions": questions} # Return update dict

    print(f"generate_questions_node: Generating questions based on background: {state.candidate_background[:100]}...")
    system_prompt = f"""
    You are an expert technical interviewer for a {COMPANY_ROLE} position.
    Based on the candidate's background provided below, generate exactly {NUM_INTERVIEW_QUESTIONS} thoughtful interview questions.
    Consider their stated experience, skills (or lack thereof), and the target role.
    Include a mix of technical (specific to their likely skills), problem-solving, and behavioral questions.
    Ensure questions are relevant and progressively challenging if possible.

    Return ONLY a Python-style list of strings, where each string is one question. Example:
    ["Question 1?", "Question 2 about specific skill?", "Question 3 behavioral?"]
    Do not include numbering or introduction/conclusion text, just the list itself.
    """

    messages = format_messages_for_openrouter(
        system_message=system_prompt,
        messages=[{
            "role": "user",
            "content": f"Candidate background:\n{state.candidate_background}\n\nGenerate {NUM_INTERVIEW_QUESTIONS} questions as a Python list of strings."
        }]
    )

    generated_questions = []
    try:
        completion = get_openrouter_completion(messages, max_tokens=1000)
        print(f"generate_questions_node: LLM completion received: {completion}")

        try:
            # ... (List parsing logic remains the same) ...
            start_idx = completion.find('[')
            end_idx = completion.rfind(']') + 1
            if start_idx != -1 and end_idx != -1:
                 list_str = completion[start_idx:end_idx]
                 generated_questions = ast.literal_eval(list_str)
                 if not isinstance(generated_questions, list): raise ValueError("Not a list")
                 generated_questions = [str(q).strip() for q in generated_questions if str(q).strip()]
            else: # Fallback parsing if brackets not found
                 print("Brackets not found, trying line splitting.")
                 generated_questions = [line.strip(' -*"') for line in completion.strip().split('\n') if line.strip()]


        except Exception as parse_e:
            print(f"generate_questions_node: Error parsing LLM list ({parse_e}). Trying line-based extraction.")
            generated_questions = [line.strip(' -*"') for line in completion.strip().split('\n') if line.strip()]


        # Validate and pad/truncate (remains the same)
        if len(generated_questions) == 0: # Ensure we don't have an empty list
            #  use defaults if no questions generated
             print("Warning: No questions parsed, using defaults.")
             generated_questions = default_questions[:NUM_INTERVIEW_QUESTIONS]
        elif len(generated_questions) < NUM_INTERVIEW_QUESTIONS:
            # Pad with default questions if fewer than required
            print(f"Padding from {len(generated_questions)} to {NUM_INTERVIEW_QUESTIONS}")
            needed = NUM_INTERVIEW_QUESTIONS - len(generated_questions)
            generated_questions.extend(default_questions[:needed])
        elif len(generated_questions) > NUM_INTERVIEW_QUESTIONS:
            # cutt off the questions if we got extra - truncaate to the required number
            print(f"Truncating from {len(generated_questions)} to {NUM_INTERVIEW_QUESTIONS}")
            generated_questions = generated_questions[:NUM_INTERVIEW_QUESTIONS]

    except Exception as e:
        print(f"generate_questions_node: Error calling LLM or processing: {e}")
        traceback.print_exc()
        generated_questions = default_questions[:NUM_INTERVIEW_QUESTIONS] # Fallback

    print(f"generate_questions_node: Final questions count: {len(generated_questions)}")
    # Return ONLY the updated non-message field
    return {"interview_questions": generated_questions}


# Node returns a dict with the message to add
def ask_question_node(state: InterviewState) -> Dict[str, List[Dict[str, str]]]:
    """
    Ask the next interview question.
    Returns a dictionary containing ONLY the new message to be added.
    """
    print("--- Executing Node: ask_question_node ---")

    if not state.interview_questions or state.current_question_index >= len(state.interview_questions):
        print(f"ask_question_node: No more questions.")
        return {} # Return empty dict if no message to add

    question = state.interview_questions[state.current_question_index]
    print(f"ask_question_node: Asking Q{state.current_question_index}: {question}")

    # Format message
    if state.current_question_index == 0:
        greeting = f"Great, thank you for sharing that, {state.candidate_name}." if state.candidate_name and state.candidate_name != "Candidate" else "Great, thank you for sharing that."
        question_message_content = f"{greeting} Let's move on to our first question:\n\n{question}"
    else:
        question_message_content = f"Thank you. Next question:\n\n{question}"

    new_message = {"role": "assistant", "content": question_message_content}
    print("ask_question_node: Returning new message.")
    # Return dict containing ONLY the new message(s) for add_messages
    return {"messages": [new_message]}

# --- END OF FILE nodes/question.py ---