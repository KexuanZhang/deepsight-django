"""
Agentic RAG Service - Handle agentic RAG operations using RagFlow Knowledge Base Agents.
"""

import logging
from typing import Dict, List, Optional, Generator, Any
from django.core.cache import cache
from rest_framework import status

from ..models import Notebook, RagFlowDataset
from infrastructure.ragflow.client import get_ragflow_client, RagFlowClientError
from core.services import NotebookBaseService

logger = logging.getLogger(__name__)


class AgenticRAGService(NotebookBaseService):
    """
    Handle agentic RAG operations using RagFlow Knowledge Base Agents.
    
    This service provides an intelligent RAG interface where agents have access to
    retrieval tools and can make decisions about how to gather and use information.
    """
    
    def __init__(self):
        super().__init__()
        self.ragflow_client = get_ragflow_client()
        self._agent_cache_timeout = 300  # 5 minutes
        self._session_cache_timeout = 1800  # 30 minutes
    
    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        pass
    
    def get_or_create_agent_session(self, notebook: Notebook, user_id: int) -> Dict:
        """
        Get or create an agent session for the notebook's dataset.
        
        Args:
            notebook: Notebook instance
            user_id: User ID for session management
            
        Returns:
            Dict with session info or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)
            
            # Check if notebook has RagFlow dataset
            if not hasattr(notebook, 'ragflow_dataset'):
                return {
                    "error": "Notebook has no RagFlow dataset",
                    "status_code": status.HTTP_400_BAD_REQUEST
                }
            
            ragflow_dataset = notebook.ragflow_dataset
            if not ragflow_dataset.is_ready():
                return {
                    "error": "RagFlow dataset is not ready",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "dataset_status": ragflow_dataset.status
                }
            
            # Check cache for existing session
            cache_key = f"ragflow_agent_session_{notebook.id}_{user_id}"
            cached_session = cache.get(cache_key)
            
            if cached_session:
                logger.info(f"Using cached agent session for notebook {notebook.id}")
                return {
                    "success": True,
                    "session": cached_session,
                    "cached": True
                }
            
            # Get knowledge base agent
            agent = self._get_knowledge_base_agent()
            if not agent:
                return {
                    "error": "No knowledge base agent available",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }
            
            # Create new session
            session_name = f"notebook_{notebook.id}_{notebook.name}_{user_id}"
            session = self.ragflow_client.create_agent_session(agent, session_name)
            
            if not session:
                return {
                    "error": "Failed to create agent session",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
                }
            
            # Cache the session
            session_info = {
                "session": session,
                "agent": agent,
                "dataset_id": ragflow_dataset.ragflow_dataset_id,
                "notebook_id": notebook.id,
                "created_for_user": user_id
            }
            
            cache.set(cache_key, session_info, timeout=self._session_cache_timeout)
            
            self.log_notebook_operation(
                "agent_session_created",
                str(notebook.id),
                user_id,
                session_id=getattr(session, 'id', 'unknown'),
                agent_name=getattr(agent, 'name', 'unknown')
            )
            
            return {
                "success": True,
                "session_info": session_info,
                "cached": False
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error creating agent session for notebook {notebook.id}: {e}")
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Failed to create agent session for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to create agent session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def ask_agent_streaming(self, notebook: Notebook, user_id: int, question: str, 
                           history: List[Dict] = None) -> Generator:
        """
        Ask the knowledge base agent a question with streaming response.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            question: Question to ask
            history: Optional conversation history
            
        Returns:
            Generator yielding streaming response chunks
        """
        try:
            # Get or create agent session
            session_result = self.get_or_create_agent_session(notebook, user_id)
            
            if not session_result.get('success'):
                # Yield error as SSE format
                error_msg = session_result.get('error', 'Unknown error')
                yield f"data: {{'type': 'error', 'message': '{error_msg}'}}\n\n"
                return
            
            session_info = session_result.get('session_info') or session_result.get('session')
            session = session_info.get('session') if isinstance(session_info, dict) else session_info
            
            # Add history context if provided
            if history:
                context_prompt = self._build_context_from_history(history)
                enhanced_question = f"{context_prompt}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Ask the agent with streaming
            logger.info(f"Asking agent for notebook {notebook.id}: {question[:100]}...")
            agent_response = self.ragflow_client.ask_agent(session, enhanced_question, stream=True)
            
            # Stream the response
            for chunk in agent_response:
                try:
                    if hasattr(chunk, 'content') and chunk.content:
                        # Format as SSE
                        content = chunk.content.replace('\n', '\\n').replace('"', '\\"')
                        yield f"data: {{'type': 'token', 'text': '{content}'}}\n\n"
                    elif isinstance(chunk, str):
                        # Handle string responses
                        content = chunk.replace('\n', '\\n').replace('"', '\\"')
                        yield f"data: {{'type': 'token', 'text': '{content}'}}\n\n"
                        
                except Exception as chunk_error:
                    logger.error(f"Error processing agent response chunk: {chunk_error}")
                    continue
            
            # Send completion signal
            yield f"data: {{'type': 'done', 'message': 'Agent response complete'}}\n\n"
            
            self.log_notebook_operation(
                "agent_question_asked",
                str(notebook.id),
                user_id,
                question_length=len(question)
            )
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error during agent query: {e}")
            yield f"data: {{'type': 'error', 'message': 'RagFlow service error: {str(e)}'}}\n\n"
            
        except Exception as e:
            logger.exception(f"Error during agent streaming query: {e}")
            yield f"data: {{'type': 'error', 'message': 'Agent query failed: {str(e)}'}}\n\n"
    
    def ask_agent_direct(self, notebook: Notebook, user_id: int, question: str, 
                        history: List[Dict] = None) -> Dict:
        """
        Ask the knowledge base agent a question with direct response.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            question: Question to ask
            history: Optional conversation history
            
        Returns:
            Dict with agent response
        """
        try:
            # Get or create agent session
            session_result = self.get_or_create_agent_session(notebook, user_id)
            
            if not session_result.get('success'):
                return session_result
            
            session_info = session_result.get('session_info') or session_result.get('session')
            session = session_info.get('session') if isinstance(session_info, dict) else session_info
            
            # Add history context if provided
            if history:
                context_prompt = self._build_context_from_history(history)
                enhanced_question = f"{context_prompt}\n\nCurrent question: {question}"
            else:
                enhanced_question = question
            
            # Ask the agent without streaming
            agent_response = self.ragflow_client.ask_agent(session, enhanced_question, stream=False)
            
            # Extract content from response
            if hasattr(agent_response, 'content'):
                content = agent_response.content
            elif isinstance(agent_response, str):
                content = agent_response
            else:
                content = str(agent_response)
            
            self.log_notebook_operation(
                "agent_question_asked_direct",
                str(notebook.id),
                user_id,
                question_length=len(question),
                response_length=len(content)
            )
            
            return {
                "success": True,
                "content": content,
                "agent_response": agent_response
            }
            
        except RagFlowClientError as e:
            logger.exception(f"RagFlow client error during direct agent query: {e}")
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)}
            }
        except Exception as e:
            logger.exception(f"Error during direct agent query: {e}")
            return {
                "error": "Agent query failed",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def clear_agent_session(self, notebook: Notebook, user_id: int) -> Dict:
        """
        Clear the agent session for a notebook.
        
        Args:
            notebook: Notebook instance
            user_id: User ID
            
        Returns:
            Dict with operation result
        """
        try:
            cache_key = f"ragflow_agent_session_{notebook.id}_{user_id}"
            cache.delete(cache_key)
            
            self.log_notebook_operation(
                "agent_session_cleared",
                str(notebook.id),
                user_id
            )
            
            return {
                "success": True,
                "message": "Agent session cleared"
            }
            
        except Exception as e:
            logger.exception(f"Error clearing agent session: {e}")
            return {
                "error": "Failed to clear agent session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)}
            }
    
    def _get_knowledge_base_agent(self):
        """Get knowledge base agent with caching."""
        cache_key = "ragflow_knowledge_base_agent"
        cached_agent = cache.get(cache_key)
        
        if cached_agent:
            return cached_agent
        
        agent = self.ragflow_client.get_knowledge_base_agent()
        if agent:
            cache.set(cache_key, agent, timeout=self._agent_cache_timeout)
        
        return agent
    
    def _build_context_from_history(self, history: List[Dict]) -> str:
        """Build context prompt from conversation history."""
        if not history:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for msg in history[-5:]:  # Use last 5 messages for context
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                context_parts.append(f"{role.title()}: {content}")
        
        return "\n".join(context_parts)
    
    def get_agent_info(self) -> Dict:
        """Get information about the current knowledge base agent."""
        try:
            agent = self._get_knowledge_base_agent()
            if not agent:
                return {
                    "available": False,
                    "error": "No knowledge base agent found"
                }
            
            return {
                "available": True,
                "name": getattr(agent, 'name', 'Unknown'),
                "id": getattr(agent, 'id', 'Unknown'),
                "description": getattr(agent, 'description', ''),
            }
            
        except Exception as e:
            logger.exception(f"Error getting agent info: {e}")
            return {
                "available": False,
                "error": str(e)
            }