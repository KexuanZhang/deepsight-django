"""
RagFlow Client - Wrapper around ragflow-sdk with error handling and configuration.
"""

import logging
import time
from typing import Dict, List, Optional, Any
from django.conf import settings
from ragflow_sdk import RAGFlow

logger = logging.getLogger(__name__)


class RagFlowClientError(Exception):
    """Base exception for RagFlow client errors."""
    pass


class RagFlowDatasetError(RagFlowClientError):
    """Exception for dataset-related errors."""
    pass


class RagFlowDocumentError(RagFlowClientError):
    """Exception for document-related errors."""
    pass


class RagFlowChatError(RagFlowClientError):
    """Exception for chat-related errors."""
    pass


class RagFlowClient:
    """
    RagFlow client wrapper with error handling, retry logic, and logging.
    
    Provides a clean interface for interacting with RagFlow API while handling
    common errors and providing comprehensive logging.
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize RagFlow client.
        
        Args:
            api_key: RagFlow API key (defaults to settings.RAGFLOW_API_KEY)
            base_url: RagFlow base URL (defaults to settings.RAGFLOW_BASE_URL)
        """
        self.api_key = api_key or getattr(settings, 'RAGFLOW_API_KEY', None)
        self.base_url = base_url or getattr(settings, 'RAGFLOW_BASE_URL', 'http://localhost:9380')
        
        if not self.api_key:
            raise RagFlowClientError("RagFlow API key is required")
        
        self.client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"RagFlow client initialized with base_url: {self.base_url}")
    
    def _retry_on_failure(self, func, *args, max_retries: int = 3, delay: float = 1.0, **kwargs):
        """
        Retry a function on failure with exponential backoff.
        
        Args:
            func: Function to retry
            *args: Function arguments
            max_retries: Maximum number of retries
            delay: Initial delay between retries
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            RagFlowClientError: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries")
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed. Last error: {e}")
        
        raise RagFlowClientError(f"Operation failed after {max_retries + 1} attempts: {last_error}")
    
    # Dataset Management
    def create_dataset(self, name: str, description: str = "", **kwargs) -> Dict:
        """
        Create a new RagFlow dataset.
        
        Args:
            name: Dataset name
            description: Dataset description
            **kwargs: Additional dataset configuration
            
        Returns:
            Dict containing dataset information
            
        Raises:
            RagFlowDatasetError: If dataset creation fails
        """
        try:
            logger.info(f"Creating RagFlow dataset: {name}")
            
            # Set default configuration
            dataset_config = {
                'name': name,
                'description': description,
                'chunk_method': getattr(settings, 'RAGFLOW_DEFAULT_CHUNK_METHOD', 'naive'),
                'embedding_model': getattr(settings, 'RAGFLOW_DEFAULT_EMBEDDING_MODEL', 'BAAI/bge-en-v1.5'),
                **kwargs
            }
            
            def _create():
                return self.client.create_dataset(**dataset_config)
            
            dataset = self._retry_on_failure(_create)
            logger.info(f"Dataset created successfully: {dataset.id}")
            
            return {
                'id': dataset.id,
                'name': dataset.name,
                'description': getattr(dataset, 'description', description),
                'status': 'created'
            }
            
        except Exception as e:
            logger.error(f"Failed to create dataset '{name}': {e}")
            raise RagFlowDatasetError(f"Failed to create dataset: {e}")
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a RagFlow dataset.
        
        Args:
            dataset_id: Dataset ID to delete
            
        Returns:
            True if successful
            
        Raises:
            RagFlowDatasetError: If deletion fails
        """
        try:
            logger.info(f"Deleting RagFlow dataset: {dataset_id}")
            
            def _delete():
                self.client.delete_datasets(ids=[dataset_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Dataset deleted successfully: {dataset_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(f"Failed to delete dataset: {e}")
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """
        Get dataset information.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            Dataset information or None if not found
        """
        try:
            datasets = self.client.list_datasets(id=dataset_id)
            if datasets:
                dataset = datasets[0]
                return {
                    'id': dataset.id,
                    'name': dataset.name,
                    'description': getattr(dataset, 'description', ''),
                    'status': getattr(dataset, 'status', 'unknown')
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get dataset '{dataset_id}': {e}")
            return None
    
    # Document Management
    def upload_document(self, dataset_id: str, content: str, display_name: str) -> Dict:
        """
        Upload a document to a RagFlow dataset.
        
        Args:
            dataset_id: Target dataset ID
            content: Document content (markdown text)
            display_name: Display name for the document
            
        Returns:
            Dict containing document information
            
        Raises:
            RagFlowDocumentError: If upload fails
        """
        try:
            logger.info(f"Uploading document '{display_name}' to dataset {dataset_id}")
            
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")
            
            dataset = datasets[0]
            
            # Prepare document for upload
            document_data = [{
                'display_name': display_name,
                'blob': content.encode('utf-8')
            }]
            
            def _upload():
                uploaded_docs = dataset.upload_documents(document_data)
                return uploaded_docs[0] if uploaded_docs else None
            
            document = self._retry_on_failure(_upload)
            
            if not document:
                raise RagFlowDocumentError("Document upload returned no result")
            
            logger.info(f"Document uploaded successfully: {document.id}")
            
            return {
                'id': document.id,
                'name': display_name,
                'status': 'uploaded'
            }
            
        except Exception as e:
            logger.error(f"Failed to upload document '{display_name}' to dataset '{dataset_id}': {e}")
            raise RagFlowDocumentError(f"Failed to upload document: {e}")
    
    def delete_document(self, dataset_id: str, document_id: str) -> bool:
        """
        Delete a document from a RagFlow dataset.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID to delete
            
        Returns:
            True if successful
            
        Raises:
            RagFlowDocumentError: If deletion fails
        """
        try:
            logger.info(f"Deleting document {document_id} from dataset {dataset_id}")
            
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")
            
            dataset = datasets[0]
            
            def _delete():
                dataset.delete_documents(ids=[document_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Document deleted successfully: {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}': {e}")
            raise RagFlowDocumentError(f"Failed to delete document: {e}")
    
    def parse_documents(self, dataset_id: str, document_ids: List[str]) -> bool:
        """
        Trigger parsing for documents in a dataset.
        
        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs to parse
            
        Returns:
            True if parsing was triggered successfully
            
        Raises:
            RagFlowDocumentError: If parsing trigger fails
        """
        try:
            logger.info(f"Triggering parsing for {len(document_ids)} documents in dataset {dataset_id}")
            
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")
            
            dataset = datasets[0]
            
            def _parse():
                dataset.async_parse_documents(document_ids)
                return True
            
            result = self._retry_on_failure(_parse)
            logger.info(f"Document parsing triggered successfully for {len(document_ids)} documents")
            return result
            
        except Exception as e:
            logger.error(f"Failed to trigger document parsing: {e}")
            raise RagFlowDocumentError(f"Failed to trigger document parsing: {e}")
    
    def get_document_status(self, dataset_id: str, document_id: str) -> Optional[Dict]:
        """
        Get document parsing status.
        
        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            
        Returns:
            Document status information or None if not found
        """
        try:
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                return None
            
            dataset = datasets[0]
            documents = dataset.list_documents(id=document_id)
            
            if documents:
                doc = documents[0]
                return {
                    'id': doc.id,
                    'name': getattr(doc, 'name', ''),
                    'status': getattr(doc, 'status', 'unknown')
                }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return None
    
    # Chat Management
    def create_chat_assistant(self, dataset_ids: List[str], name: str) -> Dict:
        """
        Create a chat assistant for datasets.
        
        Args:
            dataset_ids: List of dataset IDs to include
            name: Assistant name
            
        Returns:
            Dict containing chat assistant information
            
        Raises:
            RagFlowChatError: If chat creation fails
        """
        try:
            logger.info(f"Creating chat assistant '{name}' for {len(dataset_ids)} datasets")
            
            def _create_chat():
                return self.client.create_chat(name, dataset_ids=dataset_ids)
            
            chat = self._retry_on_failure(_create_chat)
            logger.info(f"Chat assistant created successfully: {chat.id}")
            
            return {
                'id': chat.id,
                'name': name,
                'dataset_ids': dataset_ids
            }
            
        except Exception as e:
            logger.error(f"Failed to create chat assistant '{name}': {e}")
            raise RagFlowChatError(f"Failed to create chat assistant: {e}")
    
    def delete_chat_assistant(self, chat_id: str) -> bool:
        """
        Delete a chat assistant.
        
        Args:
            chat_id: Chat assistant ID
            
        Returns:
            True if successful
            
        Raises:
            RagFlowChatError: If deletion fails
        """
        try:
            logger.info(f"Deleting chat assistant: {chat_id}")
            
            def _delete():
                self.client.delete_chats(ids=[chat_id])
                return True
            
            result = self._retry_on_failure(_delete)
            logger.info(f"Chat assistant deleted successfully: {chat_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete chat assistant '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to delete chat assistant: {e}")
    
    # Chat Completion
    def create_chat_completion(self, chat_id: str, messages: List[Dict], stream: bool = True) -> Any:
        """
        Create chat completion using RagFlow's OpenAI-compatible API.
        
        Args:
            chat_id: RagFlow chat assistant ID
            messages: List of messages in OpenAI format
            stream: Whether to stream the response
            
        Returns:
            Chat completion response (streaming or non-streaming)
            
        Raises:
            RagFlowChatError: If chat completion fails
        """
        try:
            from openai import OpenAI
            
            logger.info(f"Creating chat completion for chat {chat_id} with {len(messages)} messages")
            
            # Create OpenAI client pointing to RagFlow
            openai_client = OpenAI(
                api_key=self.api_key,
                base_url=f"{self.base_url}/api/v1/chats_openai/{chat_id}"
            )
            
            def _create_completion():
                return openai_client.chat.completions.create(
                    model="ragflow",  # Model name doesn't matter for RagFlow
                    messages=messages,
                    stream=stream,
                    extra_body={"reference": True}  # Include references in response
                )
            
            completion = self._retry_on_failure(_create_completion)
            logger.info(f"Chat completion created successfully for chat {chat_id}")
            
            return completion
            
        except Exception as e:
            logger.error(f"Failed to create chat completion for chat '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to create chat completion: {e}")
    
    # Agent Management for Agentic RAG
    def get_knowledge_base_agent(self, agent_name: str = None) -> Optional[Any]:
        """
        Get or create a knowledge base agent for agentic RAG.
        
        Args:
            agent_name: Optional name to filter agents, defaults to first KB agent found
            
        Returns:
            Agent object or None if not found
        """
        try:
            # List available agents
            agents = self.client.list_agents()
            
            # Look for knowledge base agent (either by name or type)
            kb_agent = None
            for agent in agents:
                agent_name_attr = getattr(agent, 'name', '')
                # Look for Knowledge Base Agent template or custom name
                if (agent_name and agent_name.lower() in agent_name_attr.lower()) or \
                   ('knowledge' in agent_name_attr.lower() and 'base' in agent_name_attr.lower()):
                    kb_agent = agent
                    break
            
            if not kb_agent and agents:
                # Fallback to first available agent if no KB agent found
                kb_agent = agents[0]
                logger.warning("No Knowledge Base Agent found, using first available agent")
            
            if kb_agent:
                logger.info(f"Found knowledge base agent: {getattr(kb_agent, 'name', 'Unknown')}")
                return kb_agent
            else:
                logger.error("No agents available in RagFlow")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get knowledge base agent: {e}")
            return None
    
    def create_agent_session(self, agent, session_name: str = None) -> Optional[Any]:
        """
        Create a session with a knowledge base agent.
        
        Args:
            agent: Agent object from RagFlow
            session_name: Optional session name
            
        Returns:
            Session object or None if creation failed
        """
        try:
            session = agent.create_session(name=session_name)
            logger.info(f"Created agent session: {getattr(session, 'id', 'unknown')}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create agent session: {e}")
            return None
    
    def ask_agent(self, session, question: str, stream: bool = True) -> Any:
        """
        Ask a question to the knowledge base agent.
        
        Args:
            session: Agent session object
            question: Question to ask the agent
            stream: Whether to stream the response
            
        Returns:
            Agent response (streaming or non-streaming)
            
        Raises:
            RagFlowChatError: If agent query fails
        """
        try:
            logger.info(f"Asking agent: {question[:100]}...")
            
            def _ask():
                return session.ask(question, stream=stream)
            
            response = self._retry_on_failure(_ask)
            logger.info("Agent response received successfully")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to ask agent: {e}")
            raise RagFlowChatError(f"Agent query failed: {e}")

    # Health Check
    def health_check(self) -> bool:
        """
        Check if RagFlow service is healthy.
        
        Returns:
            True if service is healthy
        """
        try:
            # Try to list datasets as a health check
            self.client.list_datasets()
            return True
        except Exception as e:
            logger.error(f"RagFlow health check failed: {e}")
            return False


# Singleton instance for global use
_ragflow_client = None


def get_ragflow_client() -> RagFlowClient:
    """
    Get or create singleton RagFlow client instance.
    
    Returns:
        RagFlowClient instance
    """
    global _ragflow_client
    if _ragflow_client is None:
        _ragflow_client = RagFlowClient()
    return _ragflow_client