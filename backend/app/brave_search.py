"""
Brave Search API Integration

Provides web search capabilities using the Brave Search API.
Used by agents for real-time research and plagiarism detection.
"""
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SearchResult:
    """Web search result"""
    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        published_date: Optional[str] = None,
        relevance_score: int = 0,
        source: Optional[str] = None
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.published_date = published_date
        self.relevance_score = relevance_score
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "published_date": self.published_date,
            "relevance_score": self.relevance_score,
            "source": self.source
        }


class BraveSearchService:
    """
    Brave Search API client for real-time web search.

    Used by:
    - TrendsKeywordsAgent: Real-time trend research and keyword discovery
    - OriginalityPlagiarismAgent: Check if content already exists online
    """

    BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"
    DEFAULT_COUNT = 10

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Brave Search service

        Args:
            api_key: Brave Search API key (if None, will be loaded from settings)
        """
        self.api_key = api_key

    @staticmethod
    async def get_api_key_from_settings(organization_id: int) -> Optional[str]:
        """
        Get Brave Search API key from organization settings

        Args:
            organization_id: Organization ID

        Returns:
            API key or None if not configured
        """
        try:
            from .database import SessionLocal
            from .models import OrganizationSettings

            db = SessionLocal()
            try:
                settings = db.query(OrganizationSettings).filter(
                    OrganizationSettings.organization_id == organization_id
                ).first()

                if settings and settings.brave_search_api_key:
                    return settings.brave_search_api_key

                return None
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error loading Brave API key from settings: {e}")
            return None

    async def search(
        self,
        query: str,
        count: int = DEFAULT_COUNT,
        freshness: Optional[str] = None  # 'day', 'week', 'month', 'year'
    ) -> List[SearchResult]:
        """
        Perform a web search using Brave Search API

        Args:
            query: Search query
            count: Number of results to return (default 10)
            freshness: Filter by freshness (day/week/month/year)

        Returns:
            List of SearchResult objects

        Raises:
            ValueError: If API key is not configured
            aiohttp.ClientError: If API request fails
        """
        if not self.api_key:
            raise ValueError(
                "Brave Search API key not configured. Please add it in Settings or get one free at https://brave.com/search/api/"
            )

        params = {
            "q": query,
            "count": count,
        }

        if freshness:
            params["freshness"] = freshness

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BRAVE_API_URL,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 401 or response.status == 403:
                        raise ValueError("Invalid Brave Search API key")

                    if response.status == 429:
                        raise ValueError(
                            "Brave Search rate limit exceeded. Please wait a moment before trying again."
                        )

                    response.raise_for_status()
                    data = await response.json()

                    web_results = data.get("web", {}).get("results", [])

                    results = []
                    for index, result in enumerate(web_results):
                        try:
                            from urllib.parse import urlparse
                            parsed_url = urlparse(result.get("url", ""))
                            source = parsed_url.hostname
                        except:
                            source = None

                        results.append(SearchResult(
                            title=result.get("title", ""),
                            url=result.get("url", ""),
                            snippet=result.get("description", ""),
                            published_date=result.get("age") or result.get("published_date"),
                            relevance_score=max(0, 100 - (index * 5)),  # Higher score for top results
                            source=source
                        ))

                    return results

        except aiohttp.ClientError as e:
            logger.error(f"Brave Search API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during Brave search: {e}")
            raise

    async def search_trends(
        self,
        topics: List[str],
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Search for trending topics

        Args:
            topics: List of topics to search for
            days_back: How many days back to search (default 7)

        Returns:
            List of trend results with topic, relevance_score, recent_articles, summary
        """
        freshness = "day" if days_back <= 1 else ("week" if days_back <= 7 else "month")

        trend_results = []

        # Add delay between requests to respect rate limits
        for i, topic in enumerate(topics):
            try:
                if i > 0:
                    await asyncio.sleep(1.5)  # 1.5 seconds between requests

                logger.info(f"Searching Brave API for topic: {topic}")

                query = f"{topic} news trends latest developments"
                results = await self.search(query, count=5, freshness=freshness)

                if results:
                    avg_score = sum(r.relevance_score for r in results) / len(results)

                    trend_results.append({
                        "topic": topic,
                        "relevance_score": round(avg_score),
                        "recent_articles": [r.to_dict() for r in results],
                        "summary": results[0].snippet if results else "No summary available"
                    })
            except Exception as e:
                logger.error(f"Failed to search trends for topic: {topic}, error: {e}")
                continue

        # Sort by relevance score
        return sorted(trend_results, key=lambda x: x["relevance_score"], reverse=True)

    async def get_recent_news(
        self,
        topic: str,
        days_back: int = 7,
        count: int = 5
    ) -> List[SearchResult]:
        """
        Get recent news for a specific topic

        Args:
            topic: Topic to search for
            days_back: How many days back to search
            count: Number of results

        Returns:
            List of SearchResult objects
        """
        freshness = "day" if days_back <= 1 else ("week" if days_back <= 7 else "month")
        query = f"{topic} latest news"
        return await self.search(query, count=count, freshness=freshness)

    async def check_plagiarism(
        self,
        content_snippets: List[str],
        max_snippets: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Check if content snippets appear online (plagiarism detection)

        Args:
            content_snippets: List of text excerpts to check
            max_snippets: Maximum number of snippets to check

        Returns:
            List of dictionaries with snippet, found_online, matches
        """
        results = []

        for i, snippet in enumerate(content_snippets[:max_snippets]):
            try:
                if i > 0:
                    await asyncio.sleep(1.5)  # Rate limiting

                # Search for exact phrase
                query = f'"{snippet[:200]}"'  # Limit to first 200 chars
                matches = await self.search(query, count=3, freshness="year")

                results.append({
                    "snippet": snippet,
                    "found_online": len(matches) > 0,
                    "matches": [m.to_dict() for m in matches],
                    "confidence": min(matches[0].relevance_score, 100) if matches else 0
                })
            except Exception as e:
                logger.error(f"Failed to check plagiarism for snippet: {snippet[:50]}..., error: {e}")
                results.append({
                    "snippet": snippet,
                    "found_online": False,
                    "matches": [],
                    "confidence": 0
                })

        return results

    async def discover_trending_topics(
        self,
        domain: str,
        count: int = 5
    ) -> List[SearchResult]:
        """
        Discover trending topics in a specific domain

        Args:
            domain: Domain/industry to search (e.g., "AI", "Marketing", "Technology")
            count: Number of results to return

        Returns:
            List of SearchResult objects
        """
        queries = [
            f"{domain} trending now",
            f"{domain} latest breakthroughs",
            f"{domain} hot topics 2025",
            f"{domain} recent developments",
        ]

        all_results = []
        seen_urls = set()

        for i, query in enumerate(queries):
            try:
                if i > 0:
                    await asyncio.sleep(1.5)

                results = await self.search(query, count=5, freshness="week")

                # Deduplicate by URL
                for result in results:
                    if result.url not in seen_urls:
                        seen_urls.add(result.url)
                        all_results.append(result)
            except Exception as e:
                logger.error(f"Failed to search for: {query}, error: {e}")
                continue

        # Sort by relevance and return top N
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return all_results[:count]

    @staticmethod
    async def test_connection(api_key: str) -> bool:
        """
        Test Brave Search API connection

        Args:
            api_key: API key to test

        Returns:
            True if connection successful, False otherwise
        """
        if not api_key or api_key == "your-brave-search-api-key":
            return False

        service = BraveSearchService(api_key=api_key)
        try:
            results = await service.search("test", count=1)
            return len(results) >= 0  # Even 0 results means API works
        except:
            return False
