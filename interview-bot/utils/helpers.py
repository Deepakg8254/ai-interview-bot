from typing import Dict, List, Any

def format_message_history(messages: List[Dict[str, str]]) -> str:
    """
    Format message history into a readable string.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Formatted conversation history
    """
    formatted = []
    for msg in messages:
        role = msg["role"].capitalize()
        content = msg["content"]
        formatted.append(f"{role}: {content}")
    
    return "\n\n".join(formatted)

def extract_key_details(text: str) -> Dict[str, Any]:
    """
    Extract key details from text using simple heuristics.
    This is a simplified version - in production, you might want to use
    more sophisticated NLP or structure extraction.
    
    Args:
        text: Text to extract details from
        
    Returns:
        Dictionary of extracted details
    """
    # This is a placeholder - you'd want to use more sophisticated
    # techniques like NER or structured output from LLMs in production
    details = {
        "experience": [],
        "skills": [],
        "education": [],
        "interests": [],
        "keywords": []
    }
    
    lines = text.split("\n")
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Very simple rule-based extraction
        lower_line = line.lower()
        if "experience" in lower_line or "work" in lower_line:
            current_section = "experience"
        elif "skill" in lower_line or "technology" in lower_line or "technologies" in lower_line:
            current_section = "skills"
        elif "educat" in lower_line or "degree" in lower_line or "university" in lower_line:
            current_section = "education"
        elif "interest" in lower_line or "hobby" in lower_line:
            current_section = "interests"
        elif current_section and line[0] in "-*•":
            details[current_section].append(line.lstrip("-*• "))
            
    return details