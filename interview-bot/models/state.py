# --- START OF FILE models/state.py ---

from typing import Dict, List, Optional, Any, Annotated, Union
from pydantic import BaseModel, Field
from langgraph.graph import add_messages # Correct import location
# Import LangChain message types
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

# Define a type alias for the messages list content
MessageListContent = Union[Dict[str, str], BaseMessage]

class InterviewState(BaseModel):
    """Represents the state of an interview session."""

    # Use Annotated and add_messages for the message list
    messages: Annotated[List[MessageListContent], add_messages] = Field(
        default_factory=list,
        description="All messages exchanged in the conversation (BaseMessage or dict)"
    )

    candidate_name: str = Field(default="",
                              description="Candidate's name extracted from introduction")

    candidate_background: str = Field(default="",
                                    description="Candidate's background details from the introduction")

    interview_questions: List[str] = Field(default_factory=list,
                                         description="List of generated interview questions")

    current_question_index: int = Field(default=0,
                                      description="Index of the current question being asked")

    answers: List[str] = Field(default_factory=list,
                             description="Candidate's answers to questions")

    answer_analyses: List[Dict[str, Any]] = Field(default_factory=list,
                                               description="Analysis of each answer through LLM")

    feedback: str = Field(default="",
                        description="Final feedback summary")

    hiring_recommendation: str = Field(default="",
                                    description="Final hiring recommendation")

    interview_complete: bool = Field(default=False,
                                   description="Flag indicating if interview is complete")

    class Config:
        arbitrary_types_allowed = True # Allow BaseMessage types

# --- END OF FILE models/state.py ---