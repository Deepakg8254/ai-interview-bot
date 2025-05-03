import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenRouter API Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model Configuration
DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324:free"

# Company Information (customize this)
COMPANY_NAME = "Logos Labs"
COMPANY_DESCRIPTION = """
Logos Labs is a leading technology company focused on creating innovative 
solutions in artificial intelligence, machine learning, and data analytics. 
We're committed to building products that make a positive impact.
"""
COMPANY_ROLE = "Software Engineer"

# Interview Configuration
NUM_INTERVIEW_QUESTIONS = 8  # Total number of questions in interview
TEMPERATURE = 0.7            # LLM temperature (creativity vs determinism)

# You can add more configuration variables as needed