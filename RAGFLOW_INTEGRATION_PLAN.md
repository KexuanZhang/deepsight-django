# RagFlow Integration Refactor Plan

## Overview

This plan outlines the comprehensive refactoring to integrate RagFlow as the RAG backend, replacing the current Milvus-based vector storage system. The key changes include:

1. **New RagFlow Dataset Model** - Manage RagFlow datasets and link them to notebooks
2. **Updated Knowledge Base Integration** - Link knowledge base items to RagFlow datasets  
3. **Simplified RAG Architecture** - Offload vector storage and retrieval to RagFlow
4. **Preserved Parser Logic** - Keep existing content parsing, use processed Markdown as RagFlow input
5. **Per-Notebook Datasets** - Each notebook gets its own RagFlow dataset (created with notebook) for isolated knowledge

## Architecture Changes

### Current Architecture
```
User -> Notebook -> KnowledgeBaseItem -> Milvus Vector Storage -> RAG Retrieval
```

### New Architecture  
```
User -> Notebook (creates) -> RagFlowDataset -> RAG Retrieval
                 |                     |              |
                 └── KnowledgeBaseItem -(content)-> RagFlow Backend Processing
                     (manages local metadata)
```

## Implementation Plan

### Phase 1: Core Infrastructure Setup

#### 1.1 New Django Models

**Create `RagFlowDataset` Model:**
- **File:** `backend/notebooks/models/ragflow_dataset.py`
- **Fields:**
  - `notebook` (OneToOneField to Notebook, ensures one dataset per notebook)
  - `ragflow_dataset_id` (CharField, stores RagFlow dataset ID)  
  - `dataset_name` (CharField, generated from notebook name + user ID)
  - `ragflow_chat_id` (CharField, stores RagFlow chat assistant ID)
  - `status` (CharField: 'creating', 'active', 'error', 'deleting')
  - `error_message` (TextField, for error handling)
  - `created_at`, `updated_at` (timestamps)
  - `metadata` (JSONField, RagFlow config and stats)

**Update `KnowledgeBaseItem` Model:**
- **File:** `backend/notebooks/models/knowledge_item.py`  
- **New Fields:**
  - `ragflow_document_id` (CharField, links to RagFlow document)
  - `ragflow_processing_status` (CharField: 'pending', 'uploading', 'parsing', 'completed', 'failed')

#### 1.2 RagFlow Service Layer

**Create `RagFlowService`:**
- **File:** `backend/notebooks/services/ragflow_service.py`
- **Methods:**
  - `create_dataset(notebook, name=None)` - Create RagFlow dataset for notebook
  - `delete_dataset(dataset_id)` - Delete RagFlow dataset
  - `upload_knowledge_item_content(knowledge_item)` - Upload KnowledgeBaseItem content to dataset
  - `delete_document(dataset_id, document_id)` - Remove document from dataset
  - `create_chat_assistant(dataset_id, name)` - Create chat assistant for dataset
  - `query_dataset(dataset_id, query)` - Query RagFlow dataset
  - `get_document_status(dataset_id, document_id)` - Check parsing status

**Create `RagFlowClient`:**  
- **File:** `backend/infrastructure/ragflow/client.py`
- **Purpose:** Wrapper around ragflow-sdk with error handling and configuration
- **Methods:** Mirror RagFlow SDK operations with retry logic and logging

#### 1.3 Database Migrations

**Migration 1:** Add RagFlowDataset model
**Migration 2:** Add new fields to KnowledgeBaseItem  
**Migration 3:** Create indexes for efficient queries

### Phase 2: Dataset Management Integration

#### 2.1 Notebook Service Updates

**Update `NotebookService`:**
- **File:** `backend/notebooks/services/notebook_service.py`  
- **Changes:**
  - Modify `create_notebook()` to automatically create RagFlow dataset
  - Add `get_notebook_dataset()` method to retrieve existing dataset
  - Update `delete_notebook()` to cleanup RagFlow dataset
  - Add error handling and rollback logic for dataset creation failures

#### 2.2 Eager Dataset Creation Strategy

**Notebook Creation Workflow:**
1. User creates notebook via API
2. `NotebookService.create_notebook()` creates Django Notebook
3. Automatically call `RagFlowService.create_dataset(notebook)`
4. Generate dataset name from notebook name + user ID  
5. Create RagFlow chat assistant for the dataset
6. Create `RagFlowDataset` record linking notebook to RagFlow dataset
7. Return notebook with dataset information

**Notebook Deletion Workflow:**
1. User deletes notebook via API
2. `NotebookService.delete_notebook()` retrieves associated RagFlowDataset
3. Call `RagFlowService.delete_dataset(dataset_id)` to cleanup RagFlow resources
4. Django cascade delete removes RagFlowDataset record
5. Delete Django Notebook and all related KnowledgeBaseItems

**Benefits of Eager Creation:**
- Dataset always available when content is added
- Consistent notebook lifecycle management
- No need to check dataset existence during operations
- Cleaner error handling - dataset creation issues surface early

**Error Handling:**
- If RagFlow dataset creation fails, rollback notebook creation entirely
- Provide clear error messages to user about dataset creation issues
- Allow retry mechanism for failed notebook creation
- Ensure no orphaned notebooks exist without datasets

### Phase 3: Knowledge Base Processing Updates

#### 3.1 Source Processing Pipeline  

**Update File/URL/Text Processing:**
- **Files:** `backend/notebooks/services/file_service.py`, `url_service.py`
- **Changes:**  
  - Keep existing parser logic (PDF, docx, webpage extraction)
  - After parsing to Markdown, upload content to RagFlow dataset
  - Create `KnowledgeBaseItem` with `ragflow_document_id`
  - Update processing status based on RagFlow parsing results

**New Processing Flow:**
1. User uploads file/URL/text to notebook
2. Existing parsers extract and convert content to Markdown
3. Create `KnowledgeBaseItem` with processed content and metadata
4. Get notebook's existing RagFlowDataset (guaranteed to exist)
5. `RagFlowService.upload_document()` uploads KnowledgeBaseItem content to dataset
6. Store `ragflow_document_id` in KnowledgeBaseItem
7. Poll RagFlow parsing status and update local status
8. Images and metadata still stored in Django/MinIO as before

#### 3.2 Celery Task Updates

**Update Background Tasks:**
- **File:** `backend/notebooks/tasks.py`
- **Changes:**
  - Modify file processing tasks to include RagFlow upload
  - Add RagFlow status polling tasks
  - Handle RagFlow API failures gracefully
  - Maintain backward compatibility during transition

### Phase 4: Chat & RAG Integration  

#### 4.1 Chat Service Refactoring

**Update `ChatService`:**
- **File:** `backend/notebooks/services/chat_service.py`  
- **Major Changes:**
  - Replace Milvus-based RAG with RagFlow chat API
  - Use RagFlow's OpenAI-compatible chat completion endpoint
  - Maintain existing chat history in Django models
  - Support both streaming and non-streaming responses

**New Chat Flow:**
1. User sends question to notebook chat
2. `ChatService` gets notebook's RagFlow dataset (guaranteed to exist)
3. Get dataset's chat assistant
4. Call RagFlow chat completion API with question and history
5. Stream response back to user
6. Save question and answer to Django chat history

#### 4.2 RAG Retrieval Updates

**Replace Current RAG Logic:**
- Remove Milvus collection management
- Remove embedding generation logic  
- Use RagFlow's built-in retrieval and ranking
- Maintain file-specific querying by using RagFlow document filtering

### Phase 5: API Layer Updates

#### 5.1 Serializer Updates

**Update Serializers:**
- **File:** `backend/notebooks/serializers/notebook_serializers.py`
- **Changes:**
  - Add RagFlow dataset information to notebook serialization
  - Include RagFlow document status in knowledge base item serialization
  - Add dataset health/status information

#### 5.2 View Updates  

**Update Existing Views:**
- **Files:** Various API view files
- **Changes:**
  - Update knowledge base views to show RagFlow status
  - Add dataset management endpoints (list, recreate, etc.)
  - Update chat endpoints to use RagFlow backend
  - Maintain API backward compatibility

**New Views:**
- `DatasetStatusView` - Get RagFlow dataset status and statistics
- `DatasetRecreateView` - Recreate dataset if corrupted
- `DocumentSyncView` - Sync document status with RagFlow

### Phase 6: Configuration & Settings

#### 6.1 Environment Configuration

**New Settings:**
```python
# backend/backend/settings/base.py
RAGFLOW_API_KEY = os.getenv('RAGFLOW_API_KEY')
RAGFLOW_BASE_URL = os.getenv('RAGFLOW_BASE_URL', 'http://localhost:9380')  
RAGFLOW_DEFAULT_CHUNK_METHOD = os.getenv('RAGFLOW_CHUNK_METHOD', 'naive')
RAGFLOW_DEFAULT_EMBEDDING_MODEL = os.getenv('RAGFLOW_EMBEDDING_MODEL', 'BAAI/bge-en-v1.5')
```

**Update Requirements:**
```txt
# backend/requirements.txt  
ragflow-sdk>=0.1.0
```

#### 6.2 Migration Strategy

**Development Migration:**
1. Add new models and services alongside existing code
2. Feature flag to toggle between Milvus and RagFlow
3. Run migration script to create RagFlow datasets for existing notebooks
4. Gradually migrate all existing content to RagFlow datasets
5. Remove Milvus code after full migration

**Production Migration:**
1. Deploy new code with feature flag disabled
2. Run data migration script to create RagFlow datasets for all existing notebooks
3. Re-upload existing knowledge base content to RagFlow datasets
4. Enable RagFlow feature flag
5. Monitor system performance and rollback if issues arise

### Phase 7: Testing & Quality Assurance

#### 7.1 Unit Tests

**New Test Files:**
- `backend/notebooks/tests/test_ragflow_service.py`
- `backend/notebooks/tests/test_ragflow_models.py`  
- `backend/infrastructure/tests/test_ragflow_client.py`

**Updated Test Files:**
- Update existing knowledge base and chat tests
- Add RagFlow integration tests  
- Mock RagFlow API calls for reliable testing

#### 7.2 Integration Tests

**End-to-End Tests:**
- Notebook creation -> dataset creation -> file upload -> chat query
- Test error handling and recovery scenarios
- Performance testing with large datasets
- Concurrent access testing

### Phase 8: Documentation & Deployment

#### 8.1 Documentation Updates

**Update Files:**
- `CLAUDE.md` - Add RagFlow setup and commands
- `README.md` - Update architecture documentation
- API documentation - Document new endpoints and changed behaviors

#### 8.2 Deployment Considerations

**New Infrastructure Requirements:**
- RagFlow server deployment and configuration
- RagFlow API key management
- Monitoring and alerting for RagFlow service health
- Backup strategy for RagFlow datasets

**Rollback Plan:**
- Keep Milvus infrastructure during transition period
- Ability to switch back to Milvus if RagFlow issues arise  
- Data export/import tools for knowledge base content

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Create RagFlow models and migrations
- [ ] Implement RagFlowService and RagFlowClient  
- [ ] Set up basic RagFlow integration and testing

### Week 3-4: Core Integration
- [ ] Update notebook creation/deletion with dataset management
- [ ] Modify knowledge base processing pipeline
- [ ] Update Celery tasks for RagFlow integration

### Week 5-6: RAG & Chat  
- [ ] Refactor ChatService to use RagFlow
- [ ] Update API endpoints and serializers
- [ ] Implement comprehensive error handling

### Week 7-8: Testing & Polish
- [ ] Comprehensive testing and bug fixes
- [ ] Performance optimization
- [ ] Documentation and deployment preparation

## Detailed Implementation Checklist

### Phase 1: Core Infrastructure Setup
- [ ] **Create RagFlowDataset Model**
  - [ ] Define model fields and relationships
  - [ ] Add model methods for dataset operations
  - [ ] Create model managers and querysets
  - [ ] Write model tests

- [ ] **Update KnowledgeBaseItem Model**
  - [ ] Add ragflow_document_id field
  - [ ] Add ragflow_processing_status field
  - [ ] Update model constraints and indexes
  - [ ] Write migration scripts

- [ ] **Create RagFlowService**
  - [ ] Implement dataset creation/deletion methods
  - [ ] Implement document upload/management methods
  - [ ] Implement chat assistant management
  - [ ] Add comprehensive error handling
  - [ ] Write service tests

- [ ] **Create RagFlowClient**
  - [ ] Wrap ragflow-sdk with error handling
  - [ ] Add retry logic and timeout handling
  - [ ] Implement logging and monitoring
  - [ ] Write client tests

### Phase 2: Dataset Management Integration
- [ ] **Update NotebookService**
  - [ ] Modify create_notebook to create dataset automatically
  - [ ] Add get_notebook_dataset method to retrieve dataset
  - [ ] Update delete_notebook for dataset cleanup
  - [ ] Add error handling and rollback logic for dataset creation failures

- [ ] **Implement Dataset Lifecycle Management**
  - [ ] Create eager dataset creation workflow
  - [ ] Integrate dataset creation into notebook creation process
  - [ ] Add chat assistant creation
  - [ ] Implement error handling and rollback logic
  - [ ] Write integration tests for creation and deletion scenarios

### Phase 3: Knowledge Base Processing Updates
- [ ] **Update File Processing**
  - [ ] Modify file_service.py to use existing dataset for upload
  - [ ] Update URL processing service for dataset integration
  - [ ] Update text processing service for dataset integration
  - [ ] Maintain existing parser logic
  - [ ] Remove dataset existence checks from content processing

- [ ] **Update Celery Tasks**
  - [ ] Modify existing processing tasks
  - [ ] Add RagFlow status polling tasks
  - [ ] Implement error handling and recovery
  - [ ] Add monitoring and logging

### Phase 4: Chat & RAG Integration
- [ ] **Refactor ChatService**
  - [ ] Replace Milvus queries with RagFlow API
  - [ ] Update streaming response handling
  - [ ] Maintain chat history functionality
  - [ ] Add file-specific querying support

- [ ] **Update RAG Logic**
  - [ ] Remove Milvus collection management
  - [ ] Remove embedding generation code
  - [ ] Implement RagFlow retrieval
  - [ ] Add document filtering capabilities

### Phase 5: API Layer Updates
- [ ] **Update Serializers**
  - [ ] Add RagFlow dataset fields to notebook serializer
  - [ ] Add RagFlow status to knowledge base item serializer
  - [ ] Add dataset health information
  - [ ] Maintain API backward compatibility

- [ ] **Update Views**
  - [ ] Update existing knowledge base views
  - [ ] Update chat views for RagFlow backend
  - [ ] Create new dataset management views
  - [ ] Add comprehensive error handling

### Phase 6: Configuration & Settings
- [ ] **Environment Configuration**
  - [ ] Add RagFlow settings to Django config
  - [ ] Update requirements.txt
  - [ ] Add environment variable documentation
  - [ ] Create configuration validation

- [ ] **Migration Strategy**
  - [ ] Implement feature flags
  - [ ] Create data migration scripts
  - [ ] Add rollback mechanisms
  - [ ] Write migration documentation

### Phase 7: Testing & Quality Assurance
- [ ] **Unit Tests**
  - [ ] Test RagFlow models
  - [ ] Test RagFlow services
  - [ ] Test RagFlow client
  - [ ] Update existing test suites

- [ ] **Integration Tests**
  - [ ] End-to-end workflow tests
  - [ ] Error handling tests
  - [ ] Performance tests
  - [ ] Concurrent access tests

### Phase 8: Documentation & Deployment
- [ ] **Documentation Updates**
  - [ ] Update CLAUDE.md with RagFlow commands
  - [ ] Update README.md with new architecture
  - [ ] Create API documentation
  - [ ] Write deployment guides

- [ ] **Deployment Preparation**
  - [ ] Set up RagFlow infrastructure
  - [ ] Create monitoring and alerting
  - [ ] Implement backup strategies
  - [ ] Prepare rollback procedures

## Benefits of This Approach

1. **Simplified Architecture** - Remove complex Milvus management code
2. **Better RAG Performance** - Leverage RagFlow's optimized retrieval algorithms
3. **Isolated Knowledge** - Per-notebook datasets provide better data isolation
4. **Reduced Maintenance** - Offload vector storage and management to RagFlow
5. **Enhanced Features** - Access to RagFlow's advanced parsing and chunking strategies
6. **Scalability** - RagFlow handles scaling vector operations
7. **Preserved Logic** - Keep existing content parsing and file management
8. **Consistent State** - Dataset always available, no need for existence checks

## Risk Mitigation

### Technical Risks
- **RagFlow API Reliability** - Implement comprehensive error handling and retry logic
- **Data Migration Issues** - Create thorough migration scripts with rollback capabilities
- **Performance Degradation** - Benchmark and optimize RagFlow integration
- **Integration Complexity** - Use feature flags for gradual migration

### Business Risks
- **Service Disruption** - Maintain parallel systems during transition
- **Data Loss** - Implement comprehensive backup and recovery procedures
- **User Experience Impact** - Maintain API compatibility and response times

## Success Metrics

1. **Performance Metrics**
   - Chat response time < 2 seconds
   - Document upload and processing time < 30 seconds
   - System availability > 99.5%

2. **Quality Metrics**
   - RAG retrieval accuracy improvement
   - Reduced false positive search results
   - User satisfaction with chat responses

3. **Operational Metrics**
   - Reduced infrastructure complexity
   - Lower maintenance overhead
   - Improved system scalability

## Conclusion

This comprehensive plan provides a structured approach to migrating from Milvus to RagFlow while maintaining system stability and user experience. The phased implementation allows for incremental progress with proper testing and validation at each step.