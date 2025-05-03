# --- START OF FILE main.py ---

import os
import sys
from typing import Dict, Any, List, Tuple, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from models.state import InterviewState
# Import the NODE functions directly from their files
from nodes.company_intro import company_intro_node
from nodes.self_intro import ask_self_intro_node
from nodes.extract_info import extract_info_node
from nodes.question import generate_questions_node, ask_question_node
from nodes.analysis import analyze_answer_node
from nodes.feedback import summarize_feedback_node
from nodes.decision import hiring_decision_node
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage # Ensure HumanMessage is imported

import traceback
import json

# --- Checkpointer Instance ---
memory = MemorySaver()

# --- create_interview_graph (Uses imported nodes) ---
def create_interview_graph() -> StateGraph:
    """
    Create the LangGraph flow for the interview process, using imported nodes.
    Nodes return specific update dictionaries. Messages handled by Annotated state.
    """
    builder = StateGraph(InterviewState)

    # Add nodes using the imported functions
    builder.add_node("company_intro", company_intro_node)
    builder.add_node("ask_self_intro", ask_self_intro_node)
    builder.add_node("extract_info", extract_info_node)
    builder.add_node("generate_questions", generate_questions_node)
    builder.add_node("ask_question", ask_question_node)
    builder.add_node("analyze_answer", analyze_answer_node)
    builder.add_node("summarize_feedback", summarize_feedback_node)
    builder.add_node("hiring_decision", hiring_decision_node)

    # Define edges
    builder.add_edge("company_intro", "ask_self_intro")
    builder.add_edge("ask_self_intro", "extract_info")
    builder.add_edge("extract_info", "generate_questions")
    builder.add_edge("generate_questions", "ask_question")
    builder.add_edge("ask_question", "analyze_answer")

    # Conditional routing
    def route_after_analysis(state: InterviewState):
        # Basic validation
        if not isinstance(state, InterviewState):
             print("Error: State in route_after_analysis is not InterviewState!")
             try: state = InterviewState(**dict(state)) # Attempt recovery
             except: return END # Cannot proceed if state is invalid

        print(f"Routing after analysis. Complete: {state.interview_complete}, Current Q: {state.current_question_index}, Total Q: {len(state.interview_questions)}")

        if state.interview_complete:
            total_questions = len(state.interview_questions) if state.interview_questions else 0
            print(f"Interview marked complete. Index {state.current_question_index}, Total questions {total_questions}.")
            return "summarize_feedback"
        else:
            if state.interview_questions and state.current_question_index < len(state.interview_questions):
                 return "ask_question"
            else:
                 print(f"Warning: Routing anomaly. Interview not complete, but index ({state.current_question_index}) meets/exceeds question count ({len(state.interview_questions) if state.interview_questions else 0}). Routing to summary.")
                 return "summarize_feedback" # Proceed to summary

    builder.add_conditional_edges(
        "analyze_answer",
        route_after_analysis,
        {
            "summarize_feedback": "summarize_feedback",
            "ask_question": "ask_question",
             END: END
        }
    )
    builder.add_edge("summarize_feedback", "hiring_decision")
    builder.add_edge("hiring_decision", END)
    builder.set_entry_point("company_intro")
    # Interrupt before nodes that NEED user input for the *next* step
    interrupt_nodes = ["extract_info", "analyze_answer"]
    print(builder)
    return builder.compile(checkpointer=memory, interrupt_before=interrupt_nodes)


# --- process_user_input (Passes only message delta) ---


# Its job is to take user input, update the state, and resume the graph.
def process_user_input(graph, current_state: InterviewState, user_input: str, thread_id: str) -> Tuple[InterviewState, List[Dict[str, str]]]:
    """
    Explicitly loads state, updates messages, saves state via checkpointer,
    then invokes the graph to continue execution.
    """
    print(f"\n--- Processing User Input for thread_id: {thread_id} ---")
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 150}

    # --- Explicit State Management ---
    loaded_state_object = None
    messages_before_update = 0
    try:
        # 1. Get the *current* state from the checkpointer
        checkpoint = graph.get_state(config=config)
        if checkpoint and checkpoint.values:
            print(f"State LOADED by Checkpointer: Type={type(checkpoint.values)}")
            # Reconstruct our InterviewState object from the checkpointer's data
            if isinstance(checkpoint.values, InterviewState):
                 loaded_state_object = checkpoint.values.copy(deep=True) # Work with a copy
            elif isinstance(checkpoint.values, dict):
                 loaded_state_object = InterviewState(**dict(checkpoint.values)) # Reconstruct
            else:
                 print("Warning: Loaded state from checkpointer is not dict or InterviewState.")
                 loaded_state_object = InterviewState() # Fallback to empty

            messages_before_update = len(loaded_state_object.messages)
            print(f"  LOADED Details: Name='{loaded_state_object.candidate_name}', BG='{loaded_state_object.candidate_background[:50]}...', QIdx={loaded_state_object.current_question_index}, Qs={len(loaded_state_object.interview_questions)}, Msgs={messages_before_update}")

        else:
            print("Checkpointer returned no prior state. Using initial empty state.")
            loaded_state_object = InterviewState() # Start fresh if no state

    except Exception as get_state_e:
         print(f"Error getting checkpoint state: {get_state_e}")
         traceback.print_exc()
         # If we can't get state, we probably can't proceed reliably
         return current_state, [{"role": "assistant", "content": f"Error loading conversation state: {get_state_e}"}]

    # 2. Manually add the user message to the messages list
    # Use HumanMessage object as that's likely what add_messages expects internally
    new_user_message = HumanMessage(content=user_input)
    # Since 'messages' uses add_messages, we provide the update dict format
    message_update_dict = {"messages": [new_user_message]}


    # 3. Explicitly update the state in the checkpointer *before* invoking
    try:
        print(f"Updating checkpointer state for {thread_id} with new user message.")
        # Pass the dictionary that add_messages reducer understands
        graph.update_state(config, message_update_dict)
        print("Checkpointer state updated.")
        # Verify the update immediately (optional debug step)
        # updated_checkpoint = graph.get_state(config=config)
        # if updated_checkpoint: print(f"  Messages count after update: {len(updated_checkpoint.values.get('messages',[]))}")

    except Exception as update_e:
        print(f"Error updating checkpoint state: {update_e}")
        traceback.print_exc()
        return loaded_state_object, [{"role": "assistant", "content": f"Error saving message: {update_e}"}]
    # --- End Explicit State Management ---


    # 4. Invoke the graph with NO input (None), forcing it to use the state just saved
    print(f"Invoking graph for thread_id '{thread_id}' with None input (expecting state load).")
    try:
        # Pass None - graph should load the state we just updated via thread_id
        invocation_result = graph.invoke(None, config=config)

        print(f"Type returned by invoke: {type(invocation_result)}")

        # --- Robust State Reconstruction ---
        final_state = None
        if isinstance(invocation_result, InterviewState):
             final_state = invocation_result
        elif isinstance(invocation_result, dict):
             try:
                 state_dict = dict(invocation_result)
                 final_state = InterviewState(**state_dict)
                 print("Successfully reconstructed InterviewState from dict.")
             except Exception as convert_error:
                 print(f"Error converting dict to InterviewState: {convert_error}")
                 traceback.print_exc()
                 return loaded_state_object, [{"role": "assistant", "content": f"Internal error processing response state: {convert_error}"}]
        else:
            print(f"Error: Unexpected type returned by graph.invoke: {type(invocation_result)}")
            return loaded_state_object, [{"role": "assistant", "content": "Sorry, an internal error occurred (unexpected invoke result type)."}]
        # --- End State Reconstruction ---

        if final_state:
             print(f"Graph invocation successful. Final state message count: {len(final_state.messages)}")
             print(f"State POST-INVOKE: Name='{final_state.candidate_name}', BG='{final_state.candidate_background[:50]}...', QIdx={final_state.current_question_index}, Qs={len(final_state.interview_questions)}")
        else:
             print("Error: Final state is None after reconstruction.")
             return loaded_state_object, [{"role": "assistant", "content": "Internal error: Failed to reconstruct final state."}]

        # Extract new assistant messages
        # Compare final message count with count *before* we added the user message explicitly
        new_assistant_messages_for_display = []
        if final_state and hasattr(final_state, 'messages'):
             # Check messages *after* the user message was added
             # The user message is at index `messages_before_update`
             if len(final_state.messages) > messages_before_update + 1:
                 newly_added_messages_objects = final_state.messages[messages_before_update + 1:]
                 print(f"Found {len(newly_added_messages_objects)} new message objects post-update.")
                 for msg_obj in newly_added_messages_objects:
                    if isinstance(msg_obj, BaseMessage) and msg_obj.type == 'ai':
                         new_assistant_messages_for_display.append({"role": "assistant", "content": msg_obj.content})
                    elif isinstance(msg_obj, dict) and msg_obj.get("role") == "assistant":
                         new_assistant_messages_for_display.append(msg_obj)
                 print(f"Extracted {len(new_assistant_messages_for_display)} new assistant messages for display.")
             else:
                  print("No new assistant messages detected after explicit state update and invoke.")
        else:
             print("Could not extract messages: final_state is invalid or missing.")

        return final_state, new_assistant_messages_for_display

    except Exception as e:
        print(f"Error during graph invocation with thread_id '{thread_id}': {e}")
        traceback.print_exc()
        # Return the state *before* the failed invoke
        return loaded_state_object, [{"role": "assistant", "content": f"Sorry, a processing error occurred: {e}"}]



# --- run_cli_interview (No changes needed from version using checkpointer+empty state) ---
def run_cli_interview():
    print("Initializing interview bot...")
    graph = create_interview_graph()
    print(graph.get_graph(xray=True).draw_mermaid())
    thread_id = "cli_session_1"
    current_state = InterviewState() # Initial state is empty

    print("Starting interview flow...")
    try:
        config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 150}
        # Start with empty state object
        initial_result = graph.invoke(InterviewState(), config=config)

        if isinstance(initial_result, InterviewState):
            current_state = initial_result
        elif isinstance(initial_result, dict):
             current_state = InterviewState(**dict(initial_result))
        else:
             raise TypeError(f"Initial invoke returned unexpected type: {type(initial_result)}")

        initial_assistant_messages = [msg for msg in current_state.messages if msg["role"] == "assistant"]
        for message in initial_assistant_messages:
            print(f"\nInterviewer: {message['content']}\n")

    except Exception as e:
        print(f"Error during initial graph invocation: {e}")
        traceback.print_exc()
        return

    # Main loop
    while True:
        if isinstance(current_state, InterviewState) and current_state.hiring_recommendation:
             print("\n--- Interview Finished ---")
             break
        if not isinstance(current_state, InterviewState):
             print(f"Critical Error: state is not InterviewState ({type(current_state)}). Halting.")
             break

        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("\nEnding interview session. Goodbye!")
            break

        print("Processing your response...")
        try:
             updated_state, new_assistant_messages = process_user_input(graph, current_state, user_input, thread_id)
             current_state = updated_state # Update main state

             if not isinstance(current_state, InterviewState):
                 print(f"CRITICAL ERROR: State became {type(current_state)} after process_user_input. Halting.")
                 break

             if not new_assistant_messages:
                 print("(No new messages from assistant)")
             for message in new_assistant_messages:
                 print(f"\nInterviewer: {message['content']}\n")

             if current_state.hiring_recommendation:
                 print("\n--- Interview Finished ---")
                 break
        except Exception as e:
             print(f"\nAn error occurred during processing: {e}")
             traceback.print_exc()
             break

if __name__ == "__main__":
    run_cli_interview()
# --- END OF FILE main.py ---