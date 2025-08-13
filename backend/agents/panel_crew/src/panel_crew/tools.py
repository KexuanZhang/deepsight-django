
import logging

from typing import Type, Any, Optional

from pydantic import BaseModel, Field
from crewai.tools.base_tool import BaseTool
from crewai_tools.tools.tavily_search_tool.tavily_search_tool import TavilySearchTool

logger = logging.getLogger(__name__)

# Constants
MAX_QUERY_LENGTH = 200

class SafeSearchToolInput(BaseModel):
    """Input schema for SafeSearchTool.
    
    Accepts flexible inputs. Prefer `query`, but also tolerates `description`,
    `content`, or a generic payload that will be normalized into a string.
    """
    query: Optional[Any] = Field(None, description="The search query string.")
    description: Optional[Any] = Field(None, description="Alternative field sometimes used by LLMs for the query.")
    content: Optional[Any] = Field(None, description="Alternative field name that may contain the query text.")

class SafeSearchTool(BaseTool):
    """Safe wrapper for TavilySearchTool that handles parameter validation.
    
    This tool provides a robust wrapper around the Tavily Search API with
    comprehensive error handling and input validation.
    """
    name: str = "Safe Tavily Search"
    description: str = (
        "A safe tool that performs web searches using the Tavily Search API. "
        "It returns search results based on the query string. Use this to find "
        "recent information, research papers, or technical details not in your training data."
    )
    args_schema: Type[BaseModel] = SafeSearchToolInput

    def __init__(self) -> None:
        """Initialize the SafeSearchTool.
        
        Args:
            search_depth: Optional Tavily search depth (e.g., "basic" or "advanced").
        """
        super().__init__()
        try:
            self._tavily_tool = TavilySearchTool(search_depth="advanced")
        except Exception as e:
            logger.warning(f"Could not initialize TavilySearchTool: {e}")
            self._tavily_tool = None

    def _run(self, query: Any = None, description: Any = None, content: Any = None, **kwargs: Any) -> str:
        """Execute the search with proper parameter handling.
        
        Args:
            query: The search query string or payload
            description: Alternate field that may contain the query string
            content: Alternate field that may contain the query string
            
        Returns:
            The search results or an appropriate error message
        """
        try:
            # Handle case where Tavily tool is not available
            if self._tavily_tool is None:
                return "Search tool is not available. Please proceed with your existing knowledge."
            
            # Select among possible fields, then normalize
            selected = query if query is not None else (description if description is not None else content)
            if selected is None and kwargs:
                # Try common keys in kwargs
                for k in ("query", "description", "content", "text", "prompt", "input"):
                    if k in kwargs and kwargs[k] is not None:
                        selected = kwargs[k]
                        break
            # Normalize query to string and flatten dict-shaped inputs used by LLMs
            normalized_query = self._normalize_query(selected)
            if not normalized_query:
                return "Error: Empty search query provided."
            
            # Execute search with error handling
            try:
                result = self._tavily_tool.run(normalized_query)
                return result if result else "No search results found."
            except Exception:
                logger.exception("Search execution failed")
                return "Search temporarily unavailable. Please use your existing knowledge to continue the discussion."
                
        except Exception as e:
            logger.exception("Search tool error")
            return f"Search tool error: {str(e)}. Please continue with your existing knowledge."
    
    def _normalize_query(self, query) -> str:
        """Normalize and validate query input.
        
        Args:
            query: The input query (may be string or other type)
            
        Returns:
            Normalized query string
        """
        # Ensure query is a string
        if not isinstance(query, str):
            # Support dict-like payloads sometimes produced by tool-calling LLMs
            if hasattr(query, 'get'):
                possible_fields = [
                    'query',
                    'q',
                    'text',
                    'content',
                    'prompt',
                    'description',
                    'input',
                ]
                for field in possible_fields:
                    value = query.get(field)
                    if isinstance(value, str) and value.strip():
                        query = value
                        break
                else:
                    # Fall back to stringifying the payload if nothing suitable found
                    query = str(query)
            else:
                query = str(query)
        
        # Clean and validate the query string
        query = query.strip()
        if not query:
            return ""
        
        return query