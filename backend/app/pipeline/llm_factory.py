from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.settings import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.openai_model,
        temperature=s.openai_temperature,
        api_key=s.openai_api_key or None,
    )
