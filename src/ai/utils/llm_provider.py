from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel

from typing import Literal

from dotenv import load_dotenv
import os

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

def init_llm(
    provider: Literal["openai", "ollama"],
    model: str,
    additional_kwargs: dict = {},
):
    if provider == "openai":
        return ChatOpenAI(model=model, **additional_kwargs)
    elif provider == "ollama":
        return ChatOllama(model=model, base_url=OLLAMA_BASE_URL, **additional_kwargs)
    else:
        raise ValueError(f"Invalid provider: {provider}")