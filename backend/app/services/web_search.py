import re
from typing import Dict, List, Optional
import httpx
from app.core.logging import logger


class WebSearchService:
    """
    Built-in, zero-dependency Web Search service.
    Queries DuckDuckGo Lite / HTML API or SearXNG to fetch live search snippets.
    """

    DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"

    @classmethod
    async def search(cls, query: str, max_results: int = 4, timeout: float = 5.0) -> List[Dict[str, str]]:
        """
        Executes a web search for the given query.
        Returns a list of dicts: [{"title": ..., "snippet": ..., "url": ...}]
        """
        results: List[Dict[str, str]] = []
        clean_query = query.strip()
        if not clean_query:
            return results

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        data = {"q": clean_query, "b": ""}

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.post(cls.DUCKDUCKGO_URL, data=data, headers=headers)
                if resp.status_code == 200:
                    results = cls._parse_duckduckgo_html(resp.text, max_results=max_results)
        except Exception as e:
            logger.warning(f"Web search query failed for '{clean_query}': {e}")

        return results

    @classmethod
    def format_search_context(cls, results: List[Dict[str, str]]) -> str:
        """Formats search results into a clean text block for prompt insertion."""
        if not results:
            return ""

        context_parts = ["--- LIVE WEB SEARCH RESULTS ---"]
        for idx, res in enumerate(results, start=1):
            title = res.get("title", "Untitled")
            snippet = res.get("snippet", "")
            url = res.get("url", "")
            context_parts.append(f"[{idx}] {title}\nURL: {url}\nSnippet: {snippet}\n")

        context_parts.append("--- END WEB SEARCH RESULTS ---")
        return "\n".join(context_parts)

    @classmethod
    def _parse_duckduckgo_html(cls, html: str, max_results: int = 4) -> List[Dict[str, str]]:
        results: List[Dict[str, str]] = []
        # Match result blocks: class="result__body"
        # Extract title (class="result__a"), snippet (class="result__snippet")
        title_matches = re.findall(r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        snippet_matches = re.findall(r'<a class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

        for i in range(min(len(title_matches), max_results)):
            url, raw_title = title_matches[i]
            title = cls._strip_tags(raw_title)
            snippet = cls._strip_tags(snippet_matches[i]) if i < len(snippet_matches) else ""

            # Extract clean URL from DuckDuckGo redirect if needed
            if "uddg=" in url:
                match = re.search(r"uddg=([^&]+)", url)
                if match:
                    import urllib.parse
                    url = urllib.parse.unquote(match.group(1))

            results.append({"title": title, "snippet": snippet, "url": url})

        return results

    @staticmethod
    def _strip_tags(text: str) -> str:
        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"\s+", " ", clean)
        return clean.strip()


web_search_service = WebSearchService()
