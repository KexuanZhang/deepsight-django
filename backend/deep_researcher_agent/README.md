# Deep Report Generator - Comprehensive Usage Guide

This guide covers the enhanced `deep_report_generator.py` which merges functionality from both the GPT and Google (Gemini) versions with comprehensive FastAPI integration support.

## Features Overview

### Multi-Model Provider Support
- **OpenAI GPT Models** (GPT-4, GPT-4 Turbo, etc.)
- **Azure OpenAI** (Enterprise deployment)
- **Google Gemini Models** (Gemini 1.5 Pro, Gemini 2.0 Flash)

### Multiple Retriever Support
- **Tavily** - Advanced AI search with web content analysis
- **Brave Search** - Privacy-focused search engine
- **Serper** - Google search API wrapper
- **You.com** - AI-powered search
- **Bing Search** - Microsoft Bing search API
- **DuckDuckGo** - Privacy-focused search (no API key required)
- **SearXNG** - Self-hosted search engine
- **Azure AI Search** - Enterprise search service

### Content Processing Capabilities
- **Text/Transcript Processing** - Clean and process transcripts
- **Academic Paper Processing** - Parse and extract insights from research papers
- **Video Processing** - Extract and caption video content
- **CSV Metadata Processing** - Handle structured metadata with filtering
- **Figure/Image Extraction** - Extract and reference figures from documents

## Quick Start

### 1. Basic Usage (Programmatic)

```python
from deep_report_generator import (
    ReportGenerationConfig,
    ModelProvider,
    RetrieverType,
    generate_report_from_config
)

# Simple report generation
config = ReportGenerationConfig(
    topic="Artificial Intelligence in Healthcare",
    article_title="AI Healthcare Research Report",
    model_provider=ModelProvider.OPENAI,
    retriever=RetrieverType.TAVILY,
    do_research=True,
    do_generate_outline=True,
    do_generate_article=True,
    do_polish_article=True
)

result = generate_report_from_config(config)
if result.success:
    print(f"Report generated: {result.article_title}")
    print(f"Files: {result.generated_files}")
else:
    print(f"Error: {result.error_message}")
```

### 2. FastAPI Integration

```python
# Use the provided fastapi_integration_example.py
python fastapi_integration_example.py

# Or integrate into your existing FastAPI app:
from deep_report_generator import generate_report_from_config, ReportGenerationConfig

@app.post("/generate-report")
async def generate_report(request: ReportRequest):
    config = ReportGenerationConfig(**request.dict())
    result = generate_report_from_config(config)
    return result
```

## Setup and Installation

### Dependencies

Create a `requirements.txt` file with the following dependencies:

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
pydantic>=2.5.0
pandas>=1.5.0
knowledge-storm
python-dotenv>=1.0.0
aiofiles>=23.2.1
httpx>=0.25.0
```

### Installation Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create secrets.toml with your API keys
cat > secrets.toml << 'EOF'
# OpenAI Configuration
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_API_TYPE = "openai"

# Google/Gemini Configuration  
GOOGLE_API_KEY = "your-google-api-key"

# Search Engine APIs
TAVILY_API_KEY = "your-tavily-api-key"
BRAVE_API_KEY = "your-brave-api-key"
SERPER_API_KEY = "your-serper-api-key"

# Optional: Other retrievers
YDC_API_KEY = "your-you-com-api-key"
BING_SEARCH_API_KEY = "your-bing-api-key"
searxng_api_url = "http://your-searxng-instance"
EOF

# 3. Create results directory
mkdir -p results/api/temp
```

## Running the FastAPI Server

### Start Server Options

```bash
# Method 1: Direct execution
python fastapi_integration_example.py

# Method 2: Using uvicorn
uvicorn fastapi_integration_example:app --host 0.0.0.0 --port 8000 --reload

# Method 3: Development mode with auto-reload
uvicorn fastapi_integration_example:app --reload --log-level debug
```

The server will start at: `http://localhost:8000`

### Access API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Testing the API

### Quick Health Check

```bash
# Test if server is running
curl http://localhost:8000/api/health

# Get available models and retrievers
curl http://localhost:8000/api/config/models
```

### Basic Report Generation Tests

#### Test 1: Simple Topic Research
```bash
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Climate Change Solutions",
    "article_title": "Climate Solutions Report",
    "model_provider": "openai",
    "retriever": "tavily",
    "do_research": true,
    "max_conv_turn": 2,
    "temperature": 0.2
  }'
```

#### Test 2: Advanced Configuration
```bash
curl -X POST "http://localhost:8000/api/reports/generate-advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Quantum Computing in Cryptography",
    "article_title": "Quantum Crypto Analysis",
    "model_provider": "google",
    "retriever": "brave",
    "max_thread_num": 15,
    "max_conv_turn": 4,
    "search_top_k": 15,
    "time_range": "month",
    "temperature": 0.1,
    "reranker_threshold": 0.6
  }'
```

#### Test 3: Content-Only Processing
```bash
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "transcript_content": "This is sample transcript content about AI research and machine learning applications in healthcare...",
    "paper_content": "# Research Paper\n\n## Abstract\nThis paper discusses recent advances in AI...",
    "article_title": "Content Analysis Report",
    "do_research": false,
    "model_provider": "openai"
  }'
```

### File Upload Testing

Create a test script for file uploads:

```bash
#!/bin/bash
# file_upload_test.sh

echo "Testing file upload endpoint..."

# Create sample files
cat > sample_transcript.txt << 'EOF'
This is a sample transcript about renewable energy research.
We discussed solar panel efficiency improvements and wind turbine innovations.
The key findings include 15% efficiency gains and reduced manufacturing costs.
Speaker 1: Our research shows significant improvements in photovoltaic cell efficiency.
Speaker 2: The cost reduction in wind turbine manufacturing is remarkable.
EOF

cat > sample_paper.md << 'EOF'
# Renewable Energy Innovations

## Abstract
This paper presents recent advances in renewable energy technologies,
focusing on solar panel efficiency and wind turbine cost reductions.

## Introduction  
Renewable energy has seen remarkable progress in recent years...

## Key Findings
- Solar panel efficiency increased by 15%
- Wind turbine manufacturing costs reduced by 20%
- Battery storage capacity improvements of 30%

## Conclusion
The renewable energy sector continues to evolve rapidly.
EOF

# Test file upload
curl -X POST "http://localhost:8000/api/reports/upload-files" \
  -F "topic=Renewable Energy Research Analysis" \
  -F "article_title=RE Research Report" \
  -F "model_provider=openai" \
  -F "retriever=tavily" \
  -F "do_research=true" \
  -F "transcript_file=@sample_transcript.txt" \
  -F "paper_file=@sample_paper.md"

echo -e "\nFile upload test completed!"

# Clean up
rm sample_transcript.txt sample_paper.md
```

```bash
# Make executable and run
chmod +x file_upload_test.sh
./file_upload_test.sh
```

### Job Management Commands

```bash
# Check job status (replace JOB_ID with actual ID)
curl -X GET "http://localhost:8000/api/reports/status/JOB_ID"

# List all jobs with pagination
curl -X GET "http://localhost:8000/api/reports/jobs?limit=10&offset=0"

# Download a report file
curl -X GET "http://localhost:8000/api/reports/download/JOB_ID/storm_gen_article_polished.md" \
  --output downloaded_report.md

# Delete a job
curl -X DELETE "http://localhost:8000/api/reports/jobs/JOB_ID"
```

### Python Test Client

Use the included `test_client.py` for comprehensive testing:

```bash
# Install httpx if not already installed
pip install httpx

# Run comprehensive test suite
python test_client.py
```

The test client performs:
- ✅ Health check validation
- ✅ Available models/retrievers discovery
- ✅ Basic report generation
- ✅ File upload testing
- ✅ Job status monitoring
- ✅ Advanced report configuration
- ✅ File download testing

### Real-time Job Monitoring

Use the `monitor_jobs.py` script for real-time monitoring:

```bash
# Monitor all jobs in real-time
python monitor_jobs.py

# Monitor a specific job
python monitor_jobs.py JOB_ID
```

The monitor displays:
- 🚀 Active jobs (queued/running)
- ✅ Recently completed jobs
- ❌ Failed jobs with error details
- 📊 Real-time progress updates

## Test Scenarios

### Scenario 1: Multi-Model Comparison
```bash
# Test OpenAI model
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Ethics", "model_provider": "openai", "retriever": "tavily"}'

# Test Google Gemini model
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI Ethics", "model_provider": "google", "retriever": "tavily"}'
```

### Scenario 2: Different Retrievers
```bash
# Test with Tavily (AI-enhanced search)
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Blockchain Technology", "retriever": "tavily"}'

# Test with Brave (Privacy-focused)
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Blockchain Technology", "retriever": "brave"}'

# Test with DuckDuckGo (No API key required)
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{"topic": "Blockchain Technology", "retriever": "duckduckgo"}'
```

### Scenario 3: Time-Filtered Research
```bash
# Recent content only (last week)
curl -X POST "http://localhost:8000/api/reports/generate-advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Latest AI Developments",
    "time_range": "week",
    "search_top_k": 20,
    "max_conv_turn": 3
  }'
```

### Scenario 4: Image Content Analysis
```bash
curl -X POST "http://localhost:8000/api/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "img_dir": "/path/to/processed/images",
    "article_title": "Image Analysis Report",
    "do_research": false,
    "model_provider": "openai"
  }'
```

## Expected Test Results

After running tests, you should see:

### Successful API Responses
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "queued",
  "message": "Report generation started successfully"
}
```

### Job Status Updates
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "running",
  "progress": "Generating article sections...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Completion Results
```json
{
  "job_id": "abc123-def456-ghi789",
  "status": "completed",
  "result": {
    "article_title": "AI Healthcare Research Report",
    "output_directory": "/path/to/results/api/AI_Healthcare_Research_Report",
    "generated_files": [
      "storm_gen_outline.txt",
      "storm_gen_article.md", 
      "storm_gen_article_polished.md",
      "AI_Healthcare_Research_Report.md"
    ],
    "processing_logs": ["API keys loaded", "Research completed", ...]
  }
}
```

### Generated Files
- **📄 storm_gen_outline.txt** - Research outline
- **📄 storm_gen_article.md** - Raw generated article  
- **📄 storm_gen_article_polished.md** - Polished final article
- **📄 {title}.md** - Post-processed clean article
- **📁 Images_{title}/** - Extracted figures and images

## Troubleshooting

### Common Issues and Solutions

#### Server Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
uvicorn fastapi_integration_example:app --port 8001
```

#### API Key Errors
```bash
# Verify secrets.toml exists and has correct keys
cat secrets.toml

# Test API key validation
curl http://localhost:8000/api/config/models
```

#### Job Failures
```bash
# Check job status for error details
curl http://localhost:8000/api/reports/status/JOB_ID

# Monitor server logs
tail -f server.log
```

#### Connection Issues
```bash
# Test server connectivity
curl http://localhost:8000/api/health

# Check if all dependencies are installed
pip list | grep -E "(fastapi|uvicorn|httpx)"
```

### Performance Monitoring

```bash
# Monitor system resources
htop

# Check server performance
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8000/api/health

# Monitor job queue
python monitor_jobs.py
```

## Configuration Options

### ReportGenerationConfig Parameters

#### Basic Settings
```python
config = ReportGenerationConfig(
    # Output configuration
    output_dir="results/api",                    # Where to save reports
    article_title="My Research Report",          # Report title
    
    # Model configuration
    model_provider=ModelProvider.OPENAI,         # OPENAI, AZURE, or GOOGLE
    retriever=RetrieverType.TAVILY,             # Search engine to use
    temperature=0.2,                            # Model creativity (0.0-2.0)
    top_p=0.4,                                  # Nucleus sampling (0.0-1.0)
    max_thread_num=10,                          # Parallel processing threads
)
```

#### Content Inputs
```python
config = ReportGenerationConfig(
    # Text content
    topic="Your research topic",                 # Main research question
    
    # File paths
    transcript_path=["path/to/transcript.txt"],  # Transcript files
    paper_path=["path/to/paper.md"],            # Research paper files
    csv_path="path/to/metadata.csv",            # Metadata CSV file
    
    # Media content
    img_dir="path/to/processed/images",         # Directory containing processed images and captions
    
    # Author information
    author_json="path/to/authors.json",         # Author metadata
)
```

#### Generation Parameters
```python
config = ReportGenerationConfig(
    # Conversation parameters
    max_conv_turn=3,                            # Max research conversations
    max_perspective=3,                          # Different viewpoints to explore
    
    # Search parameters
    search_top_k=10,                            # Search results per query
    initial_retrieval_k=150,                    # Initial document retrieval
    final_context_k=20,                         # Final context documents
    reranker_threshold=0.5,                     # Relevance threshold
    
    # Time filtering
    time_range=TimeRange.WEEK,                  # DAY, WEEK, MONTH, YEAR
    include_domains=True,                       # Include specific domains
)
```

#### Generation Flags
```python
config = ReportGenerationConfig(
    # Pipeline control
    do_research=True,                           # Perform online research
    do_generate_outline=True,                   # Generate report outline
    do_generate_article=True,                   # Generate full article
    do_polish_article=True,                     # Polish and improve article
    remove_duplicate=True,                      # Remove duplicate content
    post_processing=True,                       # Clean up formatting
    skip_rewrite_outline=False,                 # Skip outline rewriting
)
```

#### CSV Processing (Non-Interactive)
```python
config = ReportGenerationConfig(
    csv_path="metadata.csv",
    csv_session_code="SESSION_001",             # Filter by session code
    csv_date_filter="2024-01-15",              # Filter by date (YYYY-MM-DD)
)
```

## Model Provider Configuration

### OpenAI Setup
```toml
# secrets.toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_API_TYPE = "openai"
```

### Azure OpenAI Setup
```toml
# secrets.toml
OPENAI_API_KEY = "your-azure-openai-key"
OPENAI_API_TYPE = "azure"
AZURE_API_BASE = "https://your-resource.openai.azure.com/"
AZURE_API_VERSION = "2024-02-15-preview"
```

### Google Gemini Setup
```toml
# secrets.toml
GOOGLE_API_KEY = "your-google-api-key"
```

## Retriever Configuration

### Tavily (Recommended)
```toml
# secrets.toml
TAVILY_API_KEY = "your-tavily-api-key"
```

### Other Retrievers
```toml
# secrets.toml
BRAVE_API_KEY = "your-brave-api-key"
SERPER_API_KEY = "your-serper-api-key"
YDC_API_KEY = "your-you-com-api-key"
BING_SEARCH_API_KEY = "your-bing-api-key"
searxng_api_url = "http://your-searxng-instance"
AZURE_AI_SEARCH_API_KEY = "your-azure-search-key"
AZURE_AI_SEARCH_ENDPOINT = "https://your-search-service.search.windows.net"
AZURE_AI_SEARCH_INDEX = "your-search-index"
```

## Advanced Usage Examples

### 1. Multi-Source Research Report
```python
config = ReportGenerationConfig(
    topic="Climate Change Impact on Ocean Ecosystems",
    article_title="Climate-Ocean Ecosystem Analysis",
    
    # Use multiple content sources
    transcript_path=["expert_interview.txt"],
    paper_path=["research_paper.md", "supplementary_data.txt"],
    csv_path="conference_metadata.csv",
    csv_session_code="CLIMATE_2024",
    
    # Advanced model settings
    model_provider=ModelProvider.GOOGLE,
    retriever=RetrieverType.TAVILY,
    temperature=0.1,  # More focused generation
    
    # Comprehensive research
    max_conv_turn=5,
    max_perspective=4,
    search_top_k=15,
    time_range=TimeRange.MONTH,
    
    output_dir="results/climate_research"
)
```

### 2. Image Content Analysis
```python
config = ReportGenerationConfig(
    img_dir="path/to/processed/images",
    article_title="Image Content Analysis Report",

    # Focus on image processing
    do_research=False,  # Skip online research
    model_provider=ModelProvider.OPENAI,

    # Image-specific settings
    post_processing=True,
)
```

### 3. Academic Paper Deep Dive
```python
config = ReportGenerationConfig(
    paper_path=["research_paper.md"],
    topic="Deep Learning Applications in Medicine",
    
    # Academic focus
    model_provider=ModelProvider.GOOGLE,
    retriever=RetrieverType.SERPER,
    
    # Thorough analysis
    max_conv_turn=4,
    search_top_k=20,
    initial_retrieval_k=200,
    reranker_threshold=0.6,
    
    output_dir="results/academic_analysis"
)
```

## FastAPI Integration

### Basic Endpoints

#### POST `/api/reports/generate`
Basic report generation with essential parameters.

```json
{
    "topic": "Quantum Computing Applications",
    "article_title": "Quantum Computing Report",
    "model_provider": "openai",
    "retriever": "tavily",
    "do_research": true,
    "temperature": 0.2
}
```

#### POST `/api/reports/generate-advanced`
Advanced report generation with full parameter control.

```json
{
    "topic": "AI Ethics in Healthcare",
    "article_title": "Advanced AI Ethics Report",
    "model_provider": "google",
    "retriever": "brave",
    "max_thread_num": 15,
    "max_conv_turn": 4,
    "search_top_k": 15,
    "time_range": "month",
    "reranker_threshold": 0.6
}
```

#### POST `/api/reports/upload-files`
File upload endpoint for transcript, paper, CSV, and video files.

### Status Monitoring

#### GET `/api/reports/status/{job_id}`
Monitor report generation progress.

#### GET `/api/reports/jobs`
List all report generation jobs with pagination.

#### GET `/api/reports/download/{job_id}/{filename}`
Download generated report files.

## Output Files

Generated reports include:

1. **`storm_gen_outline.txt`** - Research outline
2. **`storm_gen_article.md`** - Raw generated article
3. **`storm_gen_article_polished.md`** - Polished final article
4. **`{clean_title}.md`** - Post-processed article (if enabled)
5. **`Images_{title}/`** - Extracted figures and images
6. **Query logs** - Research query tracking

## Best Practices

### 1. Model Selection
- **OpenAI GPT-4**: Best for general research and writing quality
- **Google Gemini**: Good for diverse perspectives and cost-effectiveness
- **Azure OpenAI**: Enterprise security and compliance

### 2. Retriever Selection
- **Tavily**: Best overall quality with AI-enhanced search
- **Brave**: Good for privacy-conscious research
- **Serper**: Reliable Google search results
- **DuckDuckGo**: No API key required, good for testing

### 3. Parameter Tuning
- **Temperature**: 0.1-0.3 for factual reports, 0.4-0.7 for creative writing
- **max_conv_turn**: 2-3 for quick reports, 4-5 for comprehensive research
- **search_top_k**: 10-15 for most use cases, up to 20 for complex topics

### 4. Content Processing
- Clean input text before processing
- Use specific topics rather than broad subjects
- Combine multiple content sources for comprehensive reports
- Filter CSV data appropriately for targeted analysis

## API Reference

See `fastapi_integration_example.py` for complete API documentation and examples.

The enhanced deep report generator provides a powerful, flexible system for generating comprehensive research reports with support for multiple AI models, search engines, and content types.

## Prompt Configuration

The system now supports configurable prompts for different types of reports:

### General vs Financial Prompts

The `deep_report_generator.py` supports two types of prompts:

- **General Prompts** (`PromptType.GENERAL`): Optimized for technical reports, research papers, and general analysis
- **Financial Prompts** (`PromptType.FINANCIAL`): Specialized for financial analysis, company reports, and investment research

### Usage Example

```python
from deep_report_generator import ReportGenerationConfig, ModelProvider, RetrieverType, PromptType

# For technical reports
general_config = ReportGenerationConfig(
    topic="Artificial Intelligence in Healthcare",
    output_dir="results/technical_report",
    prompt_type=PromptType.GENERAL,  # Use general prompts
    model_provider=ModelProvider.OPENAI,
    retriever=RetrieverType.TAVILY
)

# For financial analysis
financial_config = ReportGenerationConfig(
    topic="Tesla Inc Financial Performance Analysis", 
    output_dir="results/financial_analysis",
    prompt_type=PromptType.FINANCIAL,  # Use financial prompts
    model_provider=ModelProvider.OPENAI,
    retriever=RetrieverType.TAVILY
)
```

### Prompt Differences

**General Prompts** focus on:
- Technical details and innovations
- Research methodologies
- Technology trends and impacts
- Product specifications and features

**Financial Prompts** focus on:
- Revenue composition and growth drivers
- Financial metrics and ratios
- Cash flow analysis
- Investment recommendations
- Risk assessment
- Market performance indicators

The prompt configuration is automatically applied throughout all modules in the STORM pipeline, ensuring consistent analysis style across the entire report generation process. 