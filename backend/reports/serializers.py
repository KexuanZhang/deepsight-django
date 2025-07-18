from rest_framework import serializers
from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "user",
            "notebooks",
            "topic",
            "article_title",
            "old_outline",
            "selected_files_paths",
            "csv_session_code",
            "csv_date_filter",
            "model_provider",
            "retriever",
            "temperature",
            "top_p",
            "prompt_type",
            "do_research",
            "do_generate_outline",
            "do_generate_article",
            "do_polish_article",
            "remove_duplicate",
            "post_processing",
            "max_conv_turn",
            "max_perspective",
            "search_top_k",
            "initial_retrieval_k",
            "final_context_k",
            "reranker_threshold",
            "max_thread_num",
            "time_range",
            "include_domains",
            "skip_rewrite_outline",
            "domain_list",
            "search_depth",
            "status",
            "progress",
            "result_content",
            "error_message",
            "main_report_object_key",
            "file_metadata",
            "generated_files",
            "processing_logs",
            "job_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("id", "created_at", "updated_at", "user")


class ReportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new reports with validation."""

    class Meta:
        model = Report
        fields = [
            "notebooks",
            "topic",
            "article_title",
            "old_outline",
            "selected_files_paths",
            "csv_session_code",
            "csv_date_filter",
            "model_provider",
            "retriever",
            "temperature",
            "top_p",
            "prompt_type",
            "do_research",
            "do_generate_outline",
            "do_generate_article",
            "do_polish_article",
            "remove_duplicate",
            "post_processing",
            "max_conv_turn",
            "max_perspective",
            "search_top_k",
            "initial_retrieval_k",
            "final_context_k",
            "reranker_threshold",
            "max_thread_num",
            "time_range",
            "include_domains",
            "skip_rewrite_outline",
            "domain_list",
            "search_depth",
        ]

    def validate(self, data):
        """Validate that at least one input source is provided."""
        topic = data.get("topic", "").strip()
        selected_files_paths = data.get("selected_files_paths", [])

        if not topic and not selected_files_paths:
            raise serializers.ValidationError(
                "At least one of: topic or selected_files_paths must be provided"
            )

        return data

    def validate_temperature(self, value):
        """Validate temperature is in valid range."""
        if not 0.0 <= value <= 2.0:
            raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value

    def validate_top_p(self, value):
        """Validate top_p is in valid range."""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError("Top-p must be between 0.0 and 1.0")
        return value

    def validate_max_conv_turn(self, value):
        """Validate max_conv_turn is in valid range."""
        if not 1 <= value <= 10:
            raise serializers.ValidationError(
                "Max conversation turns must be between 1 and 10"
            )
        return value

    def validate_max_perspective(self, value):
        """Validate max_perspective is in valid range."""
        if not 1 <= value <= 10:
            raise serializers.ValidationError(
                "Max perspective must be between 1 and 10"
            )
        return value

    def validate_search_top_k(self, value):
        """Validate search_top_k is in valid range."""
        if not 5 <= value <= 50:
            raise serializers.ValidationError("Search top K must be between 5 and 50")
        return value

    def validate_initial_retrieval_k(self, value):
        """Validate initial_retrieval_k is in valid range."""
        if not 50 <= value <= 500:
            raise serializers.ValidationError(
                "Initial retrieval K must be between 50 and 500"
            )
        return value

    def validate_final_context_k(self, value):
        """Validate final_context_k is in valid range."""
        if not 10 <= value <= 100:
            raise serializers.ValidationError(
                "Final context K must be between 10 and 100"
            )
        return value

    def validate_reranker_threshold(self, value):
        """Validate reranker_threshold is in valid range."""
        if not 0.0 <= value <= 1.0:
            raise serializers.ValidationError(
                "Reranker threshold must be between 0.0 and 1.0"
            )
        return value

    def validate_max_thread_num(self, value):
        """Validate max_thread_num is in valid range."""
        if not 1 <= value <= 20:
            raise serializers.ValidationError(
                "Max thread number must be between 1 and 20"
            )
        return value

    def validate_time_range(self, value):
        """Convert empty string or ALL to None for time_range field."""
        if value == "" or value == "ALL":
            return None
        return value


class ReportGenerationRequestSerializer(serializers.Serializer):
    """Serializer for report generation requests (similar to FastAPI model)."""

    # Basic settings
    topic = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)
    article_title = serializers.CharField(required=False, allow_blank=True, max_length=255, default="Research Report")
    old_outline = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="User-provided outline content to use as starting point",
    )
    model_provider = serializers.ChoiceField(
        choices=Report.MODEL_PROVIDER_CHOICES, default=Report.MODEL_PROVIDER_OPENAI
    )
    retriever = serializers.ChoiceField(
        choices=Report.RETRIEVER_CHOICES, default=Report.RETRIEVER_TAVILY
    )
    temperature = serializers.FloatField(default=0.2, min_value=0.0, max_value=2.0)
    top_p = serializers.FloatField(default=0.4, min_value=0.0, max_value=1.0)
    prompt_type = serializers.ChoiceField(
        choices=Report.PROMPT_TYPE_CHOICES, default=Report.PROMPT_TYPE_GENERAL
    )

    # Generation flags
    do_research = serializers.BooleanField(default=True)
    do_generate_outline = serializers.BooleanField(default=True)
    do_generate_article = serializers.BooleanField(default=True)
    do_polish_article = serializers.BooleanField(default=True)
    remove_duplicate = serializers.BooleanField(default=True)
    post_processing = serializers.BooleanField(default=True)

    # Search and generation parameters
    max_conv_turn = serializers.IntegerField(default=3, min_value=1, max_value=10)
    max_perspective = serializers.IntegerField(default=3, min_value=1, max_value=10)
    search_top_k = serializers.IntegerField(default=10, min_value=5, max_value=50)
    initial_retrieval_k = serializers.IntegerField(
        default=150, min_value=50, max_value=500
    )
    final_context_k = serializers.IntegerField(default=20, min_value=10, max_value=100)
    reranker_threshold = serializers.FloatField(
        default=0.5, min_value=0.0, max_value=1.0
    )
    max_thread_num = serializers.IntegerField(default=10, min_value=1, max_value=20)

    # Optional parameters
    time_range = serializers.ChoiceField(
        choices=Report.TIME_RANGE_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    include_domains = serializers.BooleanField(default=False)
    skip_rewrite_outline = serializers.BooleanField(default=False)
    domain_list = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    search_depth = serializers.ChoiceField(
        choices=Report.SEARCH_DEPTH_CHOICES, default=Report.SEARCH_DEPTH_BASIC
    )

    # New flag to specify whether to include images (figure_data)
    include_image = serializers.BooleanField(default=True)

    # Content inputs from knowledge base
    selected_files_paths = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    # CSV processing options
    csv_session_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    csv_date_filter = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Figure data input
    figure_data = serializers.JSONField(
        required=False, 
        allow_null=True,
        help_text="List of figure data dictionaries with image_path and caption"
    )

    def validate(self, data):
        """Validate that at least one input source is provided."""
        topic = (data.get("topic") or "").strip()
        selected_files_paths = data.get("selected_files_paths", [])

        if not topic and not selected_files_paths:
            raise serializers.ValidationError(
                "At least one of: topic or selected_files_paths must be provided"
            )

        return data
    
    def validate_figure_data(self, value):
        """Validate figure_data structure"""
        if not value:
            return value
            
        if not isinstance(value, list):
            raise serializers.ValidationError("figure_data must be a list")
        
        for i, figure in enumerate(value):
            if not isinstance(figure, dict):
                raise serializers.ValidationError(f"Figure {i} must be a dictionary")
                
            required_fields = ['image_path', 'caption']
            missing_fields = [field for field in required_fields if field not in figure]
            if missing_fields:
                raise serializers.ValidationError(
                    f"Figure {i} missing required fields: {missing_fields}"
                )
        
        return value

    def validate_time_range(self, value):
        """Convert empty string or ALL to None for time_range field."""
        if value == "" or value == "ALL":
            return None
        return value


class ReportStatusSerializer(serializers.ModelSerializer):
    """Serializer for report status responses."""

    class Meta:
        model = Report
        fields = [
            "id",
            "job_id",
            "status",
            "progress",
            "article_title",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
