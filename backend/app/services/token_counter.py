from typing import Any, List, Union
from app.schemas.openai import ChatMessage

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")
except Exception:
    _encoder = None


def count_tokens_text(text: str) -> int:
    """Accurately count or estimate tokens for a string of text."""
    if not text:
        return 0
    if _encoder:
        try:
            return len(_encoder.encode(text))
        except Exception:
            pass
    # Standard rule of thumb: ~4 characters per token for English/code
    return max(1, len(text) // 4)


def count_chat_tokens(messages: List[Union[ChatMessage, dict]]) -> int:
    """
    Count tokens for chat messages formatted as OpenAI messages list.
    Accounts for role and message formatting overhead (~4 tokens per message).
    """
    total = 3  # Start of conversation overhead
    for msg in messages:
        total += 4  # Formatting overhead per message
        if isinstance(msg, dict):
            content = msg.get("content") or ""
            role = msg.get("role") or ""
            name = msg.get("name")
        else:
            content = msg.content or ""
            role = msg.role or ""
            name = msg.name

        if isinstance(content, str):
            total += count_tokens_text(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    total += count_tokens_text(part["text"])

        total += count_tokens_text(role)
        if name:
            total += count_tokens_text(name)

    return total
