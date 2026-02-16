"""LLM: Groq or OpenAI (OpenAI-compatible). Embeddings: Jina or OpenAI."""
from typing import List, Dict, Optional, Any
from openai import OpenAI

from app.config import settings


class LLMClient:
    """
    Chat: Groq (GROQ_API_KEY) or OpenAI (OPENAI_API_KEY for reviewers).
    Embeddings: Jina (default) or OpenAI (reviewers use their key).
    """

    def __init__(self):
        # Groq if GROQ_API_KEY set
        if settings.groq_api_key:
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
            )
            self.default_model = settings.groq_model
        else:
            if not settings.openai_api_key:
                raise ValueError("Set GROQ_API_KEY for Groq chat or OPENAI_API_KEY for OpenAI (reviewers)")
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url or None,
            )
            self.default_model = settings.openai_model

        # embedding choosing 
        self.embedding_provider = (settings.embedding_provider or "jina").lower()
        if self.embedding_provider not in ("jina", "openai"):
            raise ValueError("EMBEDDING_PROVIDER must be 'jina' or 'openai'")
        if self.embedding_provider == "jina":
            if not settings.jina_embedding_api_key:
                raise ValueError("JINA_EMBEDDING_API_KEY is required when EMBEDDING_PROVIDER=jina")
            self.embedding_client = OpenAI(
                api_key=settings.jina_embedding_api_key,
                base_url="https://api.jina.ai/v1",
            )
            self.default_embedding_model = settings.jina_embedding_model
        else:
            self.embedding_client = OpenAI(
                api_key=settings.openai_embedding_api_key or settings.openai_api_key
            )
            self.default_embedding_model = settings.openai_embedding_model

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        kwargs = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        result = {"content": message.content, "tool_calls": None}
        if message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        return result

    def embed_text(self, text: str, model: Optional[str] = None) -> List[float]:
        """Embeddings: Jina or OpenAI (OpenAI client for both)."""
        response = self.embedding_client.embeddings.create(
            model=model or self.default_embedding_model,
            input=text,
        )
        return response.data[0].embedding


llm_client = LLMClient()
