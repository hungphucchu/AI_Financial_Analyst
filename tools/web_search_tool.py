"""
Web search tool using the Tavily API for real-time financial data.

"""

from tools.base_tool import BaseTool
from config.settings import Settings


class WebSearchTool(BaseTool):
    MAX_RESULTS = 3
    SNIPPET_LENGTH = 200

    def __init__(self, settings: Settings):
        """Initialize with settings containing the Tavily API key.

        Args:
            settings: Must include ``tavily_api_key``. If empty, the tool
                      will return a helpful message instead of crashing.
        """
        self.settings = settings

    @property
    def name(self) -> str:
        return "WEB_SEARCH"

    @property
    def description(self) -> str:
        return (
            "Search the web for real-time market data, news, or current prices. "
            "Use for up-to-date information not in internal documents."
        )

    def execute(self, tool_input: str, **kwargs) -> str:
        """Search the web and return formatted results.

        Args:
            tool_input: The search query (e.g., "AAPL stock price today").
            **kwargs: Ignored. Web search doesn't use role or other context.

        Returns:
            Formatted search results with title and snippet for each result,
            or a helpful error message if the API key is missing or the
            search fails.
        """
        if not self.settings.tavily_api_key:
            return (
                "Web search unavailable: TAVILY_API_KEY not set. "
                "Get a free key at https://tavily.com and add it to your .env file."
            )

        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=self.settings.tavily_api_key)
            response = client.search(query=tool_input, max_results=self.MAX_RESULTS)

            results = []
            for r in response.get("results", []):
                snippet = r["content"][:self.SNIPPET_LENGTH]
                results.append(f"- {r['title']}: {snippet}")

            if not results:
                return f"No results found for: {tool_input}"

            return f"Web search results for '{tool_input}':\n" + "\n".join(results)

        except ImportError:
            return "Error: tavily-python not installed. Run: pip install tavily-python"
        except Exception as e:
            return f"Web search error: {e}"
