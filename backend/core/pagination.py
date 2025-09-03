"""
Custom pagination classes following Django REST Framework best practices.

Provides standardized pagination across all API endpoints with proper
performance considerations and user-friendly response formats.
"""

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardPageNumberPagination(PageNumberPagination):
    """
    Standard page-based pagination with consistent response format.
    
    Features:
    - Default page size of 20 items
    - Configurable page size via 'page_size' parameter (max 100)
    - User-friendly response format with metadata
    - Performance optimized for typical use cases
    """
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        """
        Return paginated response with comprehensive metadata.
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class LargePageNumberPagination(PageNumberPagination):
    """
    Large page pagination for data-heavy endpoints.
    
    Used for endpoints that typically need to display more data
    like knowledge base items, chat history, etc.
    """
    
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class SmallPageNumberPagination(PageNumberPagination):
    """
    Small page pagination for minimal data endpoints.
    
    Used for endpoints with lightweight data that doesn't need
    large page sizes like user lists, simple lookups, etc.
    """
    
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class StandardLimitOffsetPagination(LimitOffsetPagination):
    """
    Limit/offset based pagination for advanced use cases.
    
    Better for APIs that need specific offset capabilities
    or integration with external systems that use limit/offset.
    """
    
    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.count),
            ('limit', self.get_limit(self.request)),
            ('offset', self.get_offset(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class ChatMessagePagination(PageNumberPagination):
    """
    Specialized pagination for chat messages.
    
    Optimized for chat history display with reverse chronological order
    and reasonable page sizes for chat interfaces.
    """
    
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('has_more', self.page.has_next()),
            ('results', data)
        ]))


class NotebookPagination(PageNumberPagination):
    """
    Specialized pagination for notebooks with extended metadata.
    
    Includes additional statistics and user-friendly information
    for notebook listing interfaces.
    """
    
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 50
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        # Calculate additional statistics from the data
        total_items = sum(item.get('source_count', 0) for item in data if isinstance(item, dict))
        active_notebooks = sum(1 for item in data if isinstance(item, dict) and item.get('knowledge_item_count', 0) > 0)
        
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('stats', {
                'total_notebooks': self.page.paginator.count,
                'active_notebooks': active_notebooks,
                'total_items_across_notebooks': total_items,
            }),
            ('results', data)
        ]))