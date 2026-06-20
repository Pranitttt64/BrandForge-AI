import os
from dotenv import load_dotenv
load_dotenv()
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

def get_llm(temperature: float = 0.7) -> BaseChatModel:
    """Returns Groq primary with Gemini fallback."""
    # Read API keys from env
    groq_api_key = os.getenv("GROQ_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    # Try initializing Groq
    try:
        if not groq_api_key or groq_api_key == "your_groq_key_here":
            raise ValueError("GROQ_API_KEY not set or invalid.")
        
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            api_key=groq_api_key,
            temperature=temperature,
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "90")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        )
    except Exception as e:
        print(f"Failed to initialize Groq, falling back to Gemini: {e}")
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            google_api_key=gemini_api_key,
            temperature=temperature,
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "90")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
        )
