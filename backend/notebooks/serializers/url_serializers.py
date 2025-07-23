"""
URL processing serializers for the notebooks module.
"""

from rest_framework import serializers


class URLParseSerializer(serializers.Serializer):
    """Serializer for URL parsing requests."""
    
    url = serializers.URLField()
    upload_url_id = serializers.CharField(required=False)


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
        """Ensure either url or urls is provided."""
        url = data.get('url')
        urls = data.get('urls')
        
        if not url and not urls:
            raise serializers.ValidationError("Either 'url' or 'urls' must be provided.")
        
        if url and urls:
            raise serializers.ValidationError("Provide either 'url' or 'urls', not both.")
        
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
        """Ensure either url or urls is provided."""
        url = data.get('url')
        urls = data.get('urls')
        
        if not url and not urls:
            raise serializers.ValidationError("Either 'url' or 'urls' must be provided.")
        
        if url and urls:
            raise serializers.ValidationError("Provide either 'url' or 'urls', not both.")
        
        return data 