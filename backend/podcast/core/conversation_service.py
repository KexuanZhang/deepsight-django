"""
Conversation generation service following SOLID principles.
"""

import logging
from typing import Dict, Optional
from ..interfaces.ai_client_interface import AIClientInterface
from ..interfaces.content_detector_interface import ContentDetectorInterface
from ..interfaces.role_config_interface import RoleConfigInterface
from ..config.podcast_config import podcast_config

logger = logging.getLogger(__name__)


class ConversationService:
    """Service responsible for generating podcast conversations"""
    
    def __init__(
        self,
        ai_client: AIClientInterface,
        content_detector: ContentDetectorInterface,
        role_config: RoleConfigInterface
    ):
        self.ai_client = ai_client
        self.content_detector = content_detector
        self.role_config = role_config
        self.config = podcast_config.get_conversation_config()
    
    async def generate_conversation(self, content: str, file_metadata: Dict) -> str:
        """Generate podcast conversation from content using configured AI provider"""
        try:
            # Validate AI provider configuration
            if not self.ai_client.validate_provider():
                raise ValueError(
                    f"AI provider {self.ai_client.provider_name} is not properly configured"
                )
            
            # Detect content type and get appropriate role configuration
            content_type = self.content_detector.detect_content_type(content, file_metadata)
            role_context = self.role_config.get_content_specific_roles(content_type)
            
            # Truncate content to configured max words
            words = content.split()
            max_words = self.config['max_words']
            truncated_content = (
                " ".join(words[:max_words]) if len(words) > max_words else content
            )
            
            # Build role descriptions
            role_descriptions = []
            for name, context in role_context.items():
                desc = f"- {name}（{context['role']}）：{context['focus']}，{context['style']}"
                if "expertise" in context:
                    desc += f"，专长：{context['expertise']}"
                if "perspective" in context:
                    desc += f"，视角：{context['perspective']}"
                role_descriptions.append(desc)
            
            role_section = "\n            ".join(role_descriptions)
            
            # Get content-specific prompt template
            prompt_template = self.role_config.get_content_specific_prompt(content_type)
            
            # Build complete prompt
            prompt = prompt_template.format(
                role_section=role_section,
                yang_opening=role_context["杨飞飞"]["opening"],
                oliver_focus=role_context["奥立昆"]["focus"],
                liman_perspective=role_context["李特曼"]["perspective"],
                content=truncated_content,
            )
            
            response = self.ai_client.create_chat_completion(
                messages=[
                    {"role": "system", "content": self.config['system_prompt']},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config['temperature'],
                max_tokens=self.config['max_tokens'],
                presence_penalty=self.config['presence_penalty'],
                frequency_penalty=self.config['frequency_penalty'],
            )
            
            conversation = response.choices[0].message.content
            
            # Post-process to ensure technical focus
            conversation = self._enhance_technical_focus(conversation)
            
            logger.info(
                f"Generated conversation using {self.ai_client.provider_name} for content type '{content_type}' with {len(conversation)} characters"
            )
            return conversation
            
        except Exception as e:
            logger.error(
                f"Error generating conversation with {self.ai_client.provider_name}: {e}"
            )
            raise
    
    def _enhance_technical_focus(self, conversation: str) -> str:
        """Post-process conversation to enhance technical focus and remove fluff"""
        try:
            import re
            
            # Patterns that indicate low-value conversational content
            fluff_patterns = [
                r"<[^>]+>(?:嗯|嗯嗯|对|对的|是的|好的|没错|确实|当然|哈哈|呵呵)[^<]*</[^>]+>",
                r"<[^>]+>(?:那|那么|然后|接下来|下面|现在)[^<]*让我们[^<]*</[^>]+>",
                r"<[^>]+>(?:大家好|欢迎|感谢|谢谢)[^<]*(?:收听|观看|关注)[^<]*</[^>]+>",
                r"<[^>]+>(?:总的来说|总而言之|综上所述|最后)[^<]*(?:非常|很|真的)[^<]*(?:有趣|精彩|重要)[^<]*</[^>]+>",
            ]
            
            # Remove identified fluff patterns
            for pattern in fluff_patterns:
                conversation = re.sub(
                    pattern, "", conversation, flags=re.IGNORECASE | re.DOTALL
                )
            
            # Ensure each speaker segment has substantial technical content
            segments = re.findall(
                r"<([^/>][^>]*)>(.*?)(?=<[^/>][^>]*>|</[^>]*>|$)",
                conversation,
                re.DOTALL,
            )
            
            enhanced_segments = []
            for speaker, content in segments:
                content = content.strip()
                if content and not speaker.startswith("/"):
                    # Only keep segments with substantial technical content (> 50 characters)
                    if len(content) > 50:
                        enhanced_segments.append(f"<{speaker}>{content}</{speaker}>")
            
            # Reconstruct conversation
            enhanced_conversation = "\n\n".join(enhanced_segments)
            
            # If too much was removed, return original
            if len(enhanced_conversation) < len(conversation) * 0.5:
                logger.warning(
                    "Technical enhancement removed too much content, returning original"
                )
                return conversation
            
            return enhanced_conversation
            
        except Exception as e:
            logger.warning(
                f"Error enhancing technical focus: {e}, returning original conversation"
            )
            return conversation