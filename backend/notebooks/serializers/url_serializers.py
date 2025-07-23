"""
URL processing serializers for the notebooks module.
"""

from rest_framework import serializers
from ..utils.helpers import check_source_duplicate


class URLParseSerializer(serializers.Serializer):
    """Serializer for URL parsing requests."""
    
    url = serializers.URLField()
    upload_url_id = serializers.CharField(required=False)
    
    def validate(self, data):
        """Check for duplicate URL before processing."""
        url = data.get('url')
        if not url:
            return data
            
        # Get user and notebook from context
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check for source duplicate using raw URL for this user
            existing_item = check_source_duplicate(url, user_id, notebook_id)
            if existing_item:
                raise serializers.ValidationError({
                    'url': f'URL "{url}" already exists. Check the knowledge base.',
                    'existing_item_id': str(existing_item.id)
                })
        
        return data


class URLParseWithMediaSerializer(serializers.Serializer):
    """Serializer for URL parsing with media extraction requests."""
    url = serializers.URLField(
        help_text="URL to parse and extract media from"
    )
    upload_url_id = serializers.CharField(
        max_length=64,
        required=False,
        help_text="Custom upload ID for tracking"
    )
    
    def validate(self, data):
        """Check for duplicate URL before processing."""
        url = data.get('url')
        if not url:
            return data
            
        # Get user and notebook from context
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check for source duplicate using raw URL for this user
            existing_item = check_source_duplicate(url, user_id, notebook_id)
            if existing_item:
                raise serializers.ValidationError({
                    'url': f'URL "{url}" already exists. Check the knowledge base.',
                    'existing_item_id': str(existing_item.id)
                })
        
        return data


class URLParseDocumentSerializer(serializers.Serializer):
    """Serializer for document URL parsing requests."""
    url = serializers.URLField(
        help_text="URL to download and validate document from"
    )
    upload_url_id = serializers.CharField(
        max_length=64,
        required=False,
        help_text="Custom upload ID for tracking"
    )
    
    def validate(self, data):
        """Check for duplicate URL before processing."""
        url = data.get('url')
        if not url:
            return data
            
        # Get user and notebook from context
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check for source duplicate using raw URL for this user
            existing_item = check_source_duplicate(url, user_id, notebook_id)
            if existing_item:
                raise serializers.ValidationError({
                    'url': f'URL "{url}" already exists. Check the knowledge base.',
                    'existing_item_id': str(existing_item.id)
                })
        
        return data



class BatchURLParseSerializer(serializers.Serializer):
    """Serializer for batch URL parsing requests."""
    
    # Accept either a single URL or a list of URLs
    url = serializers.CharField(required=False)
    urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=False
    )
    upload_url_id = serializers.CharField(required=False)

    def validate(self, data):
        """Ensure either url or urls is provided and check for duplicates."""
        url = data.get('url')
        urls = data.get('urls')
        
        if not url and not urls:
            raise serializers.ValidationError("Either 'url' or 'urls' must be provided.")
        
        if url and urls:
            raise serializers.ValidationError("Provide either 'url' or 'urls', not both.")
        
        # Check for duplicates
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check single URL
            if url:
                existing_item = check_source_duplicate(url, user_id, notebook_id)
                if existing_item:
                    raise serializers.ValidationError({
                        'url': f'URL "{url}" already exists. Check the knowledge base.',
                        'existing_item_id': str(existing_item.id)
                    })
            
            # Check multiple URLs
            if urls:
                duplicate_urls = []
                for u in urls:
                    existing_item = check_source_duplicate(u, user_id, notebook_id)
                    if existing_item:
                        duplicate_urls.append({
                            'url': u,
                            'existing_item_id': str(existing_item.id)
                        })
                
                if duplicate_urls:
                    raise serializers.ValidationError({
                        'urls': 'Some URLs already exist. Check the knowledge base.',
                        'duplicates': duplicate_urls
                    })
        
        return data


class BatchURLParseWithMediaSerializer(serializers.Serializer):
    """Serializer for batch URL parsing with media extraction requests."""
    
    # Accept either a single URL or a list of URLs
    url = serializers.CharField(required=False)
    urls = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        allow_empty=False
    )
    upload_url_id = serializers.CharField(required=False)

    def validate(self, data):
        """Ensure either url or urls is provided and check for duplicates."""
        url = data.get('url')
        urls = data.get('urls')
        
        if not url and not urls:
            raise serializers.ValidationError("Either 'url' or 'urls' must be provided.")
        
        if url and urls:
            raise serializers.ValidationError("Provide either 'url' or 'urls', not both.")
        
        # Check for duplicates
        request = self.context.get('request')
        notebook_id = self.context.get('notebook_id')
        
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            
            # Check single URL
            if url:
                existing_item = check_source_duplicate(url, user_id, notebook_id)
                if existing_item:
                    raise serializers.ValidationError({
                        'url': f'URL "{url}" already exists. Check the knowledge base.',
                        'existing_item_id': str(existing_item.id)
                    })
            
            # Check multiple URLs
            if urls:
                duplicate_urls = []
                for u in urls:
                    existing_item = check_source_duplicate(u, user_id, notebook_id)
                    if existing_item:
                        duplicate_urls.append({
                            'url': u,
                            'existing_item_id': str(existing_item.id)
                        })
                
                if duplicate_urls:
                    raise serializers.ValidationError({
                        'urls': 'Some URLs already exist. Check the knowledge base.',
                        'duplicates': duplicate_urls
                    })
        
        return data 