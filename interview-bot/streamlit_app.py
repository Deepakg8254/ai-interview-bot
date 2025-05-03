# --- START OF FILE streamlit_app.py ---
import streamlit as st
from main import create_interview_graph, process_user_input
from models.state import InterviewState
# Import BaseMessage for type checking
from langchain_core.messages import BaseMessage
import traceback
import uuid

# --- App Configuration ---
st.set_page_config(page_title="AI Interview Bot", page_icon="🤖", layout="centered")
st.title("🤖 AI Technical Interview Simulator")
st.markdown("""...""") # Keep markdown

# --- Session State Initialization ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "streamlit_session"
    print(f"Initialized session with thread_id: {st.session_state.thread_id}")

if "graph" not in st.session_state:
    try:
        st.session_state.graph = create_interview_graph()
        print("Graph created successfully (with checkpointer).")
        print(st.session_state.graph.get_graph(xray=True).draw_mermaid())

    except Exception as e: st.error(f"Failed to create interview graph: {e}"); st.stop()

if "interview_state" not in st.session_state:
    st.session_state.interview_state = InterviewState()
    print("Initializing interview state and running initial graph invoke...")
    try:
        config = {"configurable": {"thread_id": st.session_state.thread_id}, "recursion_limit": 150}
        initial_result = st.session_state.graph.invoke(InterviewState(), config=config)

        # State reconstruction (should work now with updated InterviewState model)
        if isinstance(initial_result, InterviewState):
            st.session_state.interview_state = initial_result
        elif isinstance(initial_result, dict):
            try:
                # Pass the dict directly, Pydantic model should handle BaseMessage types
                st.session_state.interview_state = InterviewState(**dict(initial_result))
                print("Reconstructed InterviewState from dict (allowing BaseMessage).")
            except Exception as convert_error:
                 st.error(f"Failed to reconstruct state from dict: {convert_error}")
                 st.code(traceback.format_exc())
                 st.stop()
        else:
             raise TypeError(f"Initial invoke returned unexpected type: {type(initial_result)}")

        print(f"Initial invoke complete. State messages count: {len(st.session_state.interview_state.messages)}")
        # Initialize display messages (convert BaseMessage to dict for display)
        st.session_state.messages = []
        for msg in st.session_state.interview_state.messages:
             if isinstance(msg, BaseMessage):
                 st.session_state.messages.append({"role": msg.type, "content": msg.content})
             elif isinstance(msg, dict): # Handle if it's already a dict
                 st.session_state.messages.append(msg)
             # Add more specific checks (AIMessage -> "assistant", HumanMessage -> "user") if needed

    except Exception as e:
        # ... (error handling remains the same) ...
        st.error(f"An error occurred during interview initialization: {e}")
        st.write("Traceback:"); st.code(traceback.format_exc())
        if "messages" not in st.session_state: st.session_state.messages = []
        st.stop()


# --- Display Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display messages *from the session_state.messages list (which are dicts)*
for message in st.session_state.messages:
    # Ensure message is a dict before accessing keys
    if isinstance(message, dict) and "role" in message and "content" in message:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    else:
        print(f"Skipping display of malformed message: {message}")


# --- Handle User Input ---
interview_finished = False
# Add extra check that interview_state is the correct type
if ("interview_state" in st.session_state and
    isinstance(st.session_state.interview_state, InterviewState) and
    st.session_state.interview_state.hiring_recommendation):
     interview_finished = True

if not interview_finished:
    if prompt := st.chat_input("Your response"):
        # 1. Add user message to Streamlit display list (as dict)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # 2. Process user input
        try:
            current_state_obj = st.session_state.interview_state
            if not isinstance(current_state_obj, InterviewState):
                 print(f"Reconstructing state before processing input: {type(current_state_obj)}")
                 current_state_obj = InterviewState(**dict(current_state_obj))

            # process_user_input expects InterviewState object, user text, thread_id
            # The input to graph.invoke inside process_user_input is {"messages": [user_dict]}
            # add_messages should handle converting this dict to HumanMessage internally if needed
            new_state, new_assistant_messages_list = process_user_input(
                st.session_state.graph,
                current_state_obj,
                prompt,
                st.session_state.thread_id
            )

            # 3. Update session state
            if isinstance(new_state, InterviewState):
                 st.session_state.interview_state = new_state
                 print("State updated in session_state.")
                 # Update display messages ONLY with new assistant messages
                 # state.messages now contains BaseMessage objects
                 current_display_count = len(st.session_state.messages)
                 target_total_count = len(new_state.messages)
                 if target_total_count > current_display_count:
                      # Get the actual new messages from the authoritative state
                      new_messages_from_state = new_state.messages[current_display_count:]
                      for msg in new_messages_from_state:
                          if isinstance(msg, BaseMessage) and msg.type != 'user': # Avoid re-adding user msg
                               display_msg = {"role": msg.type, "content": msg.content}
                               st.session_state.messages.append(display_msg)
                               with st.chat_message(display_msg["role"]):
                                    st.write(display_msg["content"])
                          elif isinstance(msg, dict) and msg.get("role") != 'user':
                               # Handle if state somehow contains dicts
                               display_msg = msg
                               st.session_state.messages.append(display_msg)
                               with st.chat_message(display_msg["role"]):
                                    st.write(display_msg["content"])
                 elif target_total_count < current_display_count:
                      print("Warning: State message count decreased unexpectedly.")
                      # Force refresh display list from state?
                      st.session_state.messages = []
                      for msg in new_state.messages:
                           if isinstance(msg, BaseMessage):
                               st.session_state.messages.append({"role": msg.type, "content": msg.content})
                           elif isinstance(msg, dict):
                               st.session_state.messages.append(msg)

            else:
                 st.error(f"Processing failed to return valid state: {type(new_state)}")
                 st.stop()

            # 5. Check if interview finished
            if st.session_state.interview_state.hiring_recommendation:
                print("Interview finished signal detected. Rerunning.")
                st.rerun()

        except Exception as e:
            # ... (error handling) ...
            st.error(f"An error occurred: {str(e)}"); st.code(traceback.format_exc())

# --- Add Restart Button ---
# (remains the same)
# ...

# --- END OF FILE streamlit_app.py ---