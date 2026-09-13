import re
from typing import Any, Dict, List, Optional
from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.services.token_counter import count_chat_tokens


class RequestClassifier:
    """
    Lightweight, zero-LLM Request Classifier.
    Analyzes request characteristics in microseconds to select optimal target model capability.
    """

    # Keyword patterns for code analysis
    CODE_KEYWORDS = re.compile(
        r"\b(def|class|function|import|export|const|let|var|return|async|await|select|from|where|join|table|dockerfile|kubernetes|git|refactor|debug|unit\s+test|api|endpoint|python|javascript|typescript|golang|rust|cpp|laravel|react|vue|html|css|json|yaml|sql|bash|sh|script|regex|algorithm|recursion|pointer|interface|struct)\b",
        re.IGNORECASE,
    )

    # Code block marker
    CODE_BLOCK_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n")

    # Keyword patterns for deep reasoning & complex architecture
    REASONING_KEYWORDS = re.compile(
        r"\b(solve|proof|theorem|derive|calculus|quantum|game\s+theory|philosophy|step-by-step|chain-of-thought|deep\s+analysis|architectural\s+design|system\s+design|tradeoffs|formal|mathematical|symbolic|logic\s+puzzle|complex|np-hard|optimization|formal\s+verification)\b",
        re.IGNORECASE,
    )

    # Keyword patterns requiring live Web Search
    WEB_SEARCH_KEYWORDS = re.compile(
        r"\b(latest|current|recent|news|today|release\s+date|version|2025|2026|weather|stock\s+price|live|search\s+web|what\s+is\s+new)\b",
        re.IGNORECASE,
    )

    @classmethod
    def classify_request(cls, request: ChatCompletionRequest) -> str:
        """
        Classifies incoming request into target model capability:
        'vision' | 'tools' | 'web_search' | 'coding' | 'reasoning' | 'fast'
        """
        # 1. Vision Check: Check for image objects or base64 URLs in content
        if cls._has_vision_content(request.messages):
            return "vision"

        # 2. Tools Check: Check for tool definitions
        if request.tools and len(request.tools) > 0:
            return "coding"

        # Combine text content from user messages
        user_texts: List[str] = []
        for msg in request.messages:
            if isinstance(msg.content, str) and msg.content:
                user_texts.append(msg.content)
            elif isinstance(msg.content, list):
                for part in msg.content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        user_texts.append(part.get("text", ""))

        combined_text = "\n".join(user_texts)

        # 3. Web Search Check: Check if query requires live web information
        if cls.WEB_SEARCH_KEYWORDS.search(combined_text):
            return "web_search"

        # 4. Code Detection: Explicit code blocks or strong code keyword presence
        code_block_matches = cls.CODE_BLOCK_PATTERN.findall(combined_text)
        code_keyword_matches = cls.CODE_KEYWORDS.findall(combined_text)

        if len(code_block_matches) >= 1 or len(code_keyword_matches) >= 3:
            return "coding"

        # 5. Complex Reasoning / Math / Architecture Detection
        reasoning_matches = cls.REASONING_KEYWORDS.findall(combined_text)
        total_tokens = count_chat_tokens(request.messages)

        if len(reasoning_matches) >= 2 or (len(reasoning_matches) >= 1 and total_tokens > 1000):
            return "reasoning"

        # 6. Very Long Context (>3000 tokens) -> Reasoning model if available, else General
        if total_tokens > 3000:
            return "reasoning"

        # 7. Default / Simple Query -> Fast Model
        return "fast"

    @staticmethod
    def _has_vision_content(messages: List[ChatMessage]) -> bool:
        for msg in messages:
            if isinstance(msg.content, list):
                for item in msg.content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type in ("image_url", "image") or "image_url" in item:
                            return True
        return False


request_classifier = RequestClassifier()
