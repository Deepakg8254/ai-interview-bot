import json
import requests
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_MODEL, TEMPERATURE

def get_openrouter_completion(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = TEMPERATURE,
    max_tokens: int = 1000,
) -> str:
    """
    Send a request to OpenRouter API to get a completion.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model: Model identifier (default: deepseek-chat-v3)
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated text response
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in environment variables")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://interview-bot.example.com",  # Replace with your site
        "X-Title": "AI Interview Bot"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    
    response = requests.post(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
    )
    
    if response.status_code != 200:
        raise Exception(f"Error from OpenRouter API: {response.text}")
    
    return response.json()["choices"][0]["message"]["content"]

def format_messages_for_openrouter(
    system_message: Optional[str] = None,
    messages: List[Dict[str, str]] = None
) -> List[Dict[str, str]]:
    """
    Format messages for OpenRouter API request.
    
    Args:
        system_message: Optional system message
        messages: List of message dictionaries
        
    Returns:
        Formatted messages for API request
    """
    formatted_messages = []
    
    if system_message:
        formatted_messages.append({
            "role": "system",
            "content": system_message
        })
    
    if messages:
        for msg in messages:
            formatted_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    return formatted_messages