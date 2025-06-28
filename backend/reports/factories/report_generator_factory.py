"""
Factory for creating report generator instances.
"""

from typing import Dict, Any, Optional
from ..interfaces.report_generator_interface import ReportGeneratorInterface
from ..config.report_config import report_config


class DeepReportGeneratorAdapter(ReportGeneratorInterface):
    """Adapter for DeepReportGenerator to implement our interface"""
    
    def __init__(self, secrets_path: Optional[str] = None):
        self._generator = None
        self.secrets_path = secrets_path or report_config.get_secrets_path()
        
    @property
    def generator(self):
        """Lazy initialization of DeepReportGenerator"""
        if self._generator is None:
            try:
                # Import here to avoid early loading issues
                from agents.report_agent.deep_report_generator import DeepReportGenerator
                
                if not self.secrets_path:
                    raise ValueError("Secrets file not found")
                    
                self._generator = DeepReportGenerator(secrets_path=self.secrets_path)
                
            except ImportError as e:
                raise ImportError(f"Failed to import DeepReportGenerator: {e}")
            except Exception as e:
                raise Exception(f"Failed to initialize DeepReportGenerator: {e}")
                
        return self._generator
    
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate that the configuration is correct for report generation"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Clear cache to ensure fresh config
            report_config.clear_cache()
            
            logger.info(f"Validating report configuration: {config}")
            
            # Basic validation - ensure we have either topic or selected files
            topic = config.get('topic', '').strip()
            selected_files_paths = config.get('selected_files_paths', [])
            article_title = config.get('article_title', '').strip()
            output_dir = config.get('output_dir')
            
            # Must have either topic or selected files to generate from
            if not topic and not selected_files_paths:
                logger.error("Must provide either topic or selected_files_paths")
                return False
            
            # Must have article title
            if not article_title:
                logger.error(f"Missing or empty article_title: {article_title}")
                return False
                
            # Must have output directory  
            if not output_dir:
                logger.error(f"Missing or empty output_dir: {output_dir}")
                return False
            
            # Validate model provider
            provider = config.get('model_provider', 'openai')
            provider_config = report_config.get_model_provider_config(provider)
            logger.info(f"Model provider '{provider}' config: api_key={'***' if provider_config.get('api_key') else 'MISSING'}")
            if not provider_config.get('api_key'):
                logger.error(f"Missing API key for model provider: {provider}")
                return False
            
            # Validate retriever if it requires API key
            retriever = config.get('retriever', 'tavily')
            retriever_config = report_config.get_retriever_config(retriever)
            logger.info(f"Retriever '{retriever}' config: api_key={'***' if retriever_config.get('api_key') else 'MISSING'}")
            from ..config.retriever_configs import RetrieverConfig
            retriever_requirements = RetrieverConfig.get_retriever_requirements()
            
            # Check if this retriever requires an API key
            requires_api_key = retriever_requirements.get(retriever, {}).get('requires_api_key', True)
            
            # Free retrievers don't need API keys
            free_retrievers = ['duckduckgo', 'searxng']
            if retriever in free_retrievers:
                requires_api_key = False
            
            if requires_api_key and not retriever_config.get('api_key'):
                logger.error(f"Missing API key for retriever: {retriever}")
                return False
            
            logger.info("Report configuration validation passed")
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error during validation: {e}")
            return False
    
    def generate_report(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report based on the provided configuration"""
        try:
            # Convert our config to DeepReportGenerator config
            deep_config = self._create_deep_config(config)
            
            # Generate the report
            result = self.generator.generate_report(deep_config)
            
            # Convert result to our standard format
            return {
                'success': result.success,
                'article_title': result.article_title,
                'report_content': getattr(result, 'report_content', ''),
                'generated_files': result.generated_files or [],
                'processing_logs': result.processing_logs or [],
                'error_message': result.error_message if not result.success else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error_message': f"Report generation failed: {str(e)}"
            }
    
    def get_supported_providers(self) -> Dict[str, Any]:
        """Get information about supported AI providers and retrievers"""
        from ..config.model_providers import ModelProviderConfig
        from ..config.retriever_configs import RetrieverConfig
        
        return {
            'model_providers': ModelProviderConfig.get_supported_providers(),
            'retrievers': RetrieverConfig.get_supported_retrievers(),
            'free_retrievers': RetrieverConfig.get_free_retrievers(),
            'time_ranges': list(RetrieverConfig.get_time_range_mapping().keys()),
            'search_depths': RetrieverConfig.get_search_depth_options()
        }
    
    def cancel_generation(self, job_id: str) -> bool:
        """Cancel an ongoing report generation if possible"""
        # DeepReportGenerator doesn't currently support cancellation
        # This would need to be implemented if needed
        return False
    
    @property
    def generator_name(self) -> str:
        return "report_agent"
    
    def _create_deep_config(self, config: Dict[str, Any]) -> Any:
        """Create DeepReportGenerator configuration from our config"""
        try:
            from pathlib import Path
            import tempfile
            
            # Import required classes
            from agents.report_agent.deep_report_generator import (
                ReportGenerationConfig,
                ModelProvider,
                RetrieverType,
                TimeRange,
            )
            from agents.report_agent.prompts import PromptType
            
            # Map string values to enum values
            model_provider_map = {
                "openai": ModelProvider.OPENAI,
                "google": ModelProvider.GOOGLE,
            }
            
            retriever_map = {
                "tavily": RetrieverType.TAVILY,
                "brave": RetrieverType.BRAVE,
                "serper": RetrieverType.SERPER,
                "you": RetrieverType.YOU,
                "bing": RetrieverType.BING,
                "duckduckgo": RetrieverType.DUCKDUCKGO,
                "searxng": RetrieverType.SEARXNG,
                "azure_ai_search": RetrieverType.AZURE_AI_SEARCH,
            }
            
            time_range_map = {
                "day": TimeRange.DAY,
                "week": TimeRange.WEEK,
                "month": TimeRange.MONTH,
                "year": TimeRange.YEAR,
            }
            
            prompt_type_map = {
                "general": PromptType.GENERAL,
                "financial": PromptType.FINANCIAL
            }
            
            # Handle old_outline
            old_outline_path = None
            if config.get('old_outline') and config['old_outline'].strip():
                temp_outline_file = tempfile.NamedTemporaryFile(
                    mode="w", suffix="_old_outline.txt", delete=False
                )
                temp_outline_file.write(config['old_outline'])
                temp_outline_file.close()
                old_outline_path = temp_outline_file.name
            
            # Create the configuration
            deep_config = ReportGenerationConfig(
                topic=config.get('topic') or config.get('article_title', f"Report_{config.get('report_id', 'Unknown')}"),
                article_title=config.get('article_title') or f"Report_{config.get('report_id', 'Unknown')}",
                output_dir=str(config['output_dir']),
                report_id=config.get('report_id'),
                model_provider=model_provider_map.get(
                    config.get('model_provider', 'openai'), ModelProvider.OPENAI
                ),
                retriever=retriever_map.get(
                    config.get('retriever', 'tavily'), RetrieverType.TAVILY
                ),
                temperature=config.get('temperature', 0.2),
                top_p=config.get('top_p', 0.4),
                prompt_type=prompt_type_map.get(
                    config.get('prompt_type', 'general'), PromptType.GENERAL
                ),
                do_research=config.get('do_research', True),
                do_generate_outline=config.get('do_generate_outline', True),
                do_generate_article=config.get('do_generate_article', True),
                do_polish_article=config.get('do_polish_article', True),
                remove_duplicate=config.get('remove_duplicate', True),
                post_processing=config.get('post_processing', True),
                max_conv_turn=config.get('max_conv_turn', 3),
                max_perspective=config.get('max_perspective', 3),
                search_top_k=config.get('search_top_k', 10),
                initial_retrieval_k=config.get('initial_retrieval_k', 150),
                final_context_k=config.get('final_context_k', 20),
                reranker_threshold=config.get('reranker_threshold', 0.5),
                max_thread_num=config.get('max_thread_num', 10),
                time_range=time_range_map.get(config.get('time_range'))
                if config.get('time_range') else None,
                include_domains=config.get('include_domains', False),
                skip_rewrite_outline=config.get('skip_rewrite_outline', False),
                whitelist_domains=config.get('domain_list', []) if config.get('domain_list') else None,
                search_depth=config.get('search_depth', 'basic'),
                old_outline_path=old_outline_path,
                selected_files_paths=config.get('selected_files_paths', []),
                csv_session_code=config.get('csv_session_code', ''),
                csv_date_filter=config.get('csv_date_filter', ''),
            )
            
            # Add input content if provided (no file paths, direct content like podcast)
            if config.get('text_input'):
                deep_config.text_input = config['text_input']
            if config.get('caption_files'):
                deep_config.caption_files = config['caption_files']
            
            return deep_config
            
        except Exception as e:
            raise Exception(f"Failed to create DeepReportGenerator config: {e}")


class ReportGeneratorFactory:
    """Factory for creating report generator instances"""
    
    @staticmethod
    def create_generator(generator_type: str = 'deep_researcher') -> ReportGeneratorInterface:
        """Create report generator based on type"""
        if generator_type == 'deep_researcher':
            return DeepReportGeneratorAdapter()
        else:
            raise ValueError(f"Unknown report generator type: {generator_type}")
    
    @staticmethod
    def get_available_generators() -> list:
        """Get list of available report generator types"""
        return ['deep_researcher']