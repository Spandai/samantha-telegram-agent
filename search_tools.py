"""
Web search tools for Samantha using DuckDuckGo
Free, unlimited searches with intelligent result processing
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import aiohttp
from urllib.parse import quote_plus
import re

logger = logging.getLogger(__name__)

class DuckDuckGoSearch:
    def __init__(self):
        self.base_url = "https://api.duckduckgo.com/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    async def search(self, query: str, max_results: int = 5) -> Dict[str, any]:
        """
        Perform DuckDuckGo search and return formatted results
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Dictionary with search results and metadata
        """
        try:
            # Clean and prepare query
            clean_query = self._clean_query(query)
            
            # Get instant answer first (direct facts)
            instant_result = await self._get_instant_answer(clean_query)
            
            # Get web results
            web_results = await self._get_web_results(clean_query, max_results)
            
            return {
                'query': query,
                'instant_answer': instant_result,
                'web_results': web_results,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'DuckDuckGo'
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                'query': query,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }

    async def _get_instant_answer(self, query: str) -> Optional[str]:
        """Get DuckDuckGo instant answer for direct facts"""
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': query,
                    'format': 'json',
                    'no_html': '1',
                    'skip_disambig': '1'
                }
                
                async with session.get(self.base_url, params=params, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Check for abstract (Wikipedia-style info)
                        if data.get('Abstract'):
                            return f"{data['Abstract']} (Source: {data.get('AbstractSource', 'Unknown')})"
                        
                        # Check for definition
                        if data.get('Definition'):
                            return f"{data['Definition']} (Source: {data.get('DefinitionSource', 'Unknown')})"
                        
                        # Check for answer
                        if data.get('Answer'):
                            return data['Answer']
                            
        except Exception as e:
            logger.debug(f"No instant answer found: {e}")
            
        return None

    async def _get_web_results(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Get web search results from DuckDuckGo"""
        try:
            # Use DuckDuckGo HTML search (more reliable than API for web results)
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=self.headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        return self._parse_html_results(html_content, max_results)
                        
        except Exception as e:
            logger.error(f"Web search error: {e}")
            
        return []

    def _parse_html_results(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Parse HTML results from DuckDuckGo"""
        results = []
        
        try:
            # Simple regex parsing (could be improved with BeautifulSoup if needed)
            # This is a basic implementation - in production you'd want more robust parsing
            
            # Find result blocks
            result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
            snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>([^<]*)</a>'
            
            links = re.findall(result_pattern, html)
            snippets = re.findall(snippet_pattern, html)
            
            for i, (url, title) in enumerate(links[:max_results]):
                snippet = snippets[i] if i < len(snippets) else ""
                
                results.append({
                    'title': self._clean_text(title),
                    'url': url,
                    'snippet': self._clean_text(snippet)
                })
                
        except Exception as e:
            logger.error(f"HTML parsing error: {e}")
            
        return results

    def _clean_query(self, query: str) -> str:
        """Clean and optimize search query"""
        # Remove special characters that might interfere
        query = re.sub(r'[^\w\s\-\+\.]', ' ', query)
        # Remove extra spaces
        query = ' '.join(query.split())
        return query.strip()

    def _clean_text(self, text: str) -> str:
        """Clean HTML and formatting from text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#x27;', "'")
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text.strip()

class SearchManager:
    """High-level search manager with caching and optimization"""
    
    def __init__(self):
        self.ddg = DuckDuckGoSearch()
        self.search_cache = {}  # Simple in-memory cache
        self.cache_ttl = 3600  # 1 hour cache
        
    async def smart_search(self, query: str, context: str = None) -> str:
        """
        Perform intelligent search with caching and result formatting
        
        Args:
            query: Search query
            context: Optional context to improve search
            
        Returns:
            Formatted search results string
        """
        # Check cache first
        cache_key = query.lower().strip()
        if self._is_cached(cache_key):
            logger.debug(f"Using cached results for: {query}")
            return self.search_cache[cache_key]['results']
        
        # Perform search
        results = await self.ddg.search(query)
        
        # Format results for AI consumption
        formatted_results = self._format_for_ai(results)
        
        # Cache results
        self._cache_results(cache_key, formatted_results)
        
        return formatted_results

    def _is_cached(self, cache_key: str) -> bool:
        """Check if results are cached and still valid"""
        if cache_key not in self.search_cache:
            return False
            
        cached_time = self.search_cache[cache_key]['timestamp']
        current_time = datetime.utcnow().timestamp()
        
        return (current_time - cached_time) < self.cache_ttl

    def _cache_results(self, cache_key: str, results: str) -> None:
        """Cache search results"""
        self.search_cache[cache_key] = {
            'results': results,
            'timestamp': datetime.utcnow().timestamp()
        }

    def _format_for_ai(self, results: Dict) -> str:
        """Format search results for AI consumption"""
        if 'error' in results:
            return f"❌ Erreur de recherche: {results['error']}"
        
        formatted_parts = []
        
        # Add instant answer if available
        if results.get('instant_answer'):
            formatted_parts.append(f"📋 RÉPONSE DIRECTE:\n{results['instant_answer']}\n")
        
        # Add web results
        web_results = results.get('web_results', [])
        if web_results:
            formatted_parts.append("🔍 RÉSULTATS WEB:")
            for i, result in enumerate(web_results, 1):
                formatted_parts.append(f"{i}. **{result['title']}**")
                if result.get('snippet'):
                    formatted_parts.append(f"   {result['snippet']}")
                formatted_parts.append(f"   🔗 {result['url']}\n")
        
        if not formatted_parts:
            return f"ℹ️ Aucun résultat trouvé pour: {results['query']}"
        
        return "\n".join(formatted_parts)

# Global search manager instance
search_manager = SearchManager()