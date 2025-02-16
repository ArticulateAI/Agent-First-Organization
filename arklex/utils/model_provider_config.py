from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

LLM_PROVIDERS = ["openai", "gemini", "anthropic"]

PROVIDER_MAP = {
    "anthropic": ChatAnthropic,
    "gemini": ChatGoogleGenerativeAI,
    "openai": ChatOpenAI  
}

PROVIDER_EMBEDDINGS = {
    "anthropic": HuggingFaceEmbeddings,
    "gemini": GoogleGenerativeAIEmbeddings,
    "openai": OpenAIEmbeddings 
}
PROVIDER_EMBEDDING_MODELS = {
    "anthropic": "sentence-transformers/all-mpnet-base-v2",
    "gemini": "models/embedding-001",
    "openai": "text-embedding-ada-002"
}