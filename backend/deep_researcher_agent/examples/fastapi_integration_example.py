# FastAPI Integration Example for Deep Report Generator
# This file demonstrates how to integrate the enhanced deep_report_generator.py
# into your FastAPI backend following the integration guide

import sys
import os
import uuid
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Add the deep-researcher-agent directory to Python path
CURRENT_DIR = Path(__file__).parent
DEEP_RESEARCHER_DIR = CURRENT_DIR
sys.path.insert(0, str(DEEP_RESEARCHER_DIR))

# Import report generator components
from deep_report_generator import (
    DeepReportGenerator,
    ReportGenerationConfig,
    ReportGenerationResult,
    ModelProvider,
    RetrieverType,
    TimeRange,
    generate_report_from_config
)

# FastAPI app
app = FastAPI(
    title="Deep Research Report Generator API",
    description="Generate comprehensive research reports using AI",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for report jobs
report_jobs: Dict[str, Dict] = {}

# Pydantic models for API
class ReportRequest(BaseModel):
    # Content inputs
    topic: Optional[str] = None
    transcript_content: Optional[str] = None
    paper_content: Optional[str] = None
    article_title: str = "Research Report"
    
    # Model and retriever configuration
    model_provider: ModelProvider = ModelProvider.OPENAI
    retriever: RetrieverType = RetrieverType.TAVILY
    
    # Generation parameters
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    top_p: float = Field(default=0.4, ge=0.0, le=1.0)
    max_conv_turn: int = Field(default=3, ge=1, le=10)
    max_perspective: int = Field(default=3, ge=1, le=10)
    search_top_k: int = Field(default=10, ge=1, le=50)
    
    # Generation flags
    do_research: bool = True
    do_generate_outline: bool = True
    do_generate_article: bool = True
    do_polish_article: bool = True
    remove_duplicate: bool = True
    post_processing: bool = True
    
    # Optional parameters
    time_range: Optional[TimeRange] = None
    include_domains: bool = False
    skip_rewrite_outline: bool = False
    
    # CSV processing (when CSV is uploaded separately)
    csv_session_code: Optional[str] = None
    csv_date_filter: Optional[str] = None  # Format: YYYY-MM-DD
    
    # Video processing
    video_url: Optional[str] = None


class AdvancedReportRequest(BaseModel):
    """Extended request model with all available options"""
    # Basic content
    topic: Optional[str] = None
    article_title: str = "Advanced Research Report"
    
    # Model configuration
    model_provider: ModelProvider = ModelProvider.OPENAI
    retriever: RetrieverType = RetrieverType.TAVILY
    temperature: float = 0.2
    top_p: float = 0.4
    
    # Advanced generation parameters
    max_thread_num: int = Field(default=10, ge=1, le=20)
    max_conv_turn: int = Field(default=3, ge=1, le=10)
    max_perspective: int = Field(default=3, ge=1, le=10)
    search_top_k: int = Field(default=10, ge=1, le=50)
    initial_retrieval_k: int = Field(default=150, ge=50, le=500)
    final_context_k: int = Field(default=20, ge=10, le=100)
    reranker_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Generation flags
    do_research: bool = True
    do_generate_outline: bool = True
    do_generate_article: bool = True
    do_polish_article: bool = True
    remove_duplicate: bool = True
    post_processing: bool = True
    
    # Optional parameters
    time_range: Optional[TimeRange] = None
    include_domains: bool = False
    skip_rewrite_outline: bool = False
    
    # File and CSV processing
    csv_session_code: Optional[str] = None
    csv_date_filter: Optional[str] = None
    video_url: Optional[str] = None


class ReportResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: str
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobSummary(BaseModel):
    job_id: str
    status: str
    progress: str
    article_title: str
    model_provider: str
    retriever: str
    created_at: datetime
    has_result: bool


# Background task function
def run_report_generation_task(job_id: str, config: ReportGenerationConfig):
    """Background task to run report generation"""
    try:
        report_jobs[job_id]["status"] = "running"
        report_jobs[job_id]["progress"] = "Starting report generation..."
        report_jobs[job_id]["updated_at"] = datetime.now()
        
        # Generate the report
        result = generate_report_from_config(
            config, 
            secrets_path=str(DEEP_RESEARCHER_DIR / "secrets.toml")
        )
        
        if result.success:
            report_jobs[job_id]["status"] = "completed"
            report_jobs[job_id]["progress"] = "Report generation completed successfully"
            report_jobs[job_id]["result"] = {
                "article_title": result.article_title,
                "output_directory": result.output_directory,
                "generated_files": result.generated_files,
                "processing_logs": result.processing_logs
            }
        else:
            report_jobs[job_id]["status"] = "failed"
            report_jobs[job_id]["progress"] = "Report generation failed"
            report_jobs[job_id]["error"] = result.error_message
            
        report_jobs[job_id]["updated_at"] = datetime.now()
            
    except Exception as e:
        logging.exception(f"Report generation failed for job {job_id}")
        report_jobs[job_id]["status"] = "failed"
        report_jobs[job_id]["progress"] = "Report generation failed with exception"
        report_jobs[job_id]["error"] = str(e)
        report_jobs[job_id]["updated_at"] = datetime.now()


# API endpoints
@app.post("/api/reports/generate", response_model=ReportResponse)
async def generate_research_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks
):
    """Generate a research report with basic configuration"""
    # Validate inputs
    if not request.topic and not request.transcript_content and not request.paper_content:
        raise HTTPException(
            status_code=400,
            detail="Either topic, transcript_content, or paper_content must be provided"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create configuration
    config = ReportGenerationConfig(
        topic=request.topic,
        article_title=request.article_title,
        output_dir=str(DEEP_RESEARCHER_DIR / "results" / "api"),
        model_provider=request.model_provider,
        retriever=request.retriever,
        temperature=request.temperature,
        top_p=request.top_p,
        max_conv_turn=request.max_conv_turn,
        max_perspective=request.max_perspective,
        search_top_k=request.search_top_k,
        do_research=request.do_research,
        do_generate_outline=request.do_generate_outline,
        do_generate_article=request.do_generate_article,
        do_polish_article=request.do_polish_article,
        remove_duplicate=request.remove_duplicate,
        post_processing=request.post_processing,
        time_range=request.time_range,
        include_domains=request.include_domains,
        skip_rewrite_outline=request.skip_rewrite_outline,
        csv_session_code=request.csv_session_code,
        csv_date_filter=request.csv_date_filter,
        video_url=request.video_url,
    )
    
    # Handle content inputs by creating temporary files
    temp_files = []
    
    if request.transcript_content:
        temp_dir = DEEP_RESEARCHER_DIR / "results" / "api" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = temp_dir / f"transcript_{job_id}.txt"
        transcript_file.write_text(request.transcript_content, encoding='utf-8')
        config.transcript_path = [str(transcript_file)]
        temp_files.append(str(transcript_file))
    
    if request.paper_content:
        temp_dir = DEEP_RESEARCHER_DIR / "results" / "api" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        paper_file = temp_dir / f"paper_{job_id}.md"
        paper_file.write_text(request.paper_content, encoding='utf-8')
        config.paper_path = [str(paper_file)]
        temp_files.append(str(paper_file))
    
    # Store job information
    report_jobs[job_id] = {
        "status": "queued",
        "config": config,
        "progress": "Job queued for processing",
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "article_title": config.article_title,
        "model_provider": config.model_provider.value,
        "retriever": config.retriever.value,
        "temp_files": temp_files
    }
    
    # Start background task
    background_tasks.add_task(run_report_generation_task, job_id, config)
    
    return ReportResponse(
        job_id=job_id,
        status="queued",
        message="Report generation started successfully"
    )


@app.post("/api/reports/generate-advanced", response_model=ReportResponse)
async def generate_advanced_research_report(
    request: AdvancedReportRequest,
    background_tasks: BackgroundTasks
):
    """Generate a research report with advanced configuration options"""
    if not request.topic:
        raise HTTPException(
            status_code=400,
            detail="Topic must be provided for advanced report generation"
        )
    
    job_id = str(uuid.uuid4())
    
    # Create advanced configuration
    config = ReportGenerationConfig(
        topic=request.topic,
        article_title=request.article_title,
        output_dir=str(DEEP_RESEARCHER_DIR / "results" / "api"),
        model_provider=request.model_provider,
        retriever=request.retriever,
        temperature=request.temperature,
        top_p=request.top_p,
        max_thread_num=request.max_thread_num,
        max_conv_turn=request.max_conv_turn,
        max_perspective=request.max_perspective,
        search_top_k=request.search_top_k,
        initial_retrieval_k=request.initial_retrieval_k,
        final_context_k=request.final_context_k,
        reranker_threshold=request.reranker_threshold,
        do_research=request.do_research,
        do_generate_outline=request.do_generate_outline,
        do_generate_article=request.do_generate_article,
        do_polish_article=request.do_polish_article,
        remove_duplicate=request.remove_duplicate,
        post_processing=request.post_processing,
        time_range=request.time_range,
        include_domains=request.include_domains,
        skip_rewrite_outline=request.skip_rewrite_outline,
        csv_session_code=request.csv_session_code,
        csv_date_filter=request.csv_date_filter,
        video_url=request.video_url,
    )
    
    # Store job information
    report_jobs[job_id] = {
        "status": "queued",
        "config": config,
        "progress": "Advanced job queued for processing",
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "article_title": config.article_title,
        "model_provider": config.model_provider.value,
        "retriever": config.retriever.value,
        "temp_files": []
    }
    
    # Start background task
    background_tasks.add_task(run_report_generation_task, job_id, config)
    
    return ReportResponse(
        job_id=job_id,
        status="queued",
        message="Advanced report generation started successfully"
    )


@app.post("/api/reports/upload-files", response_model=ReportResponse)
async def generate_report_with_files(
    background_tasks: BackgroundTasks,
    topic: Optional[str] = Form(None),
    article_title: str = Form("File-based Research Report"),
    model_provider: ModelProvider = Form(ModelProvider.OPENAI),
    retriever: RetrieverType = Form(RetrieverType.TAVILY),
    do_research: bool = Form(True),
    transcript_file: Optional[UploadFile] = File(None),
    paper_file: Optional[UploadFile] = File(None),
    csv_file: Optional[UploadFile] = File(None),
    video_file: Optional[UploadFile] = File(None),
):
    """Generate a report using uploaded files"""
    
    if not topic and not transcript_file and not paper_file:
        raise HTTPException(
            status_code=400,
            detail="Either topic or file uploads (transcript/paper) must be provided"
        )
    
    job_id = str(uuid.uuid4())
    temp_dir = DEEP_RESEARCHER_DIR / "results" / "api" / "temp" / job_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Save uploaded files
    config = ReportGenerationConfig(
        topic=topic,
        article_title=article_title,
        output_dir=str(DEEP_RESEARCHER_DIR / "results" / "api"),
        model_provider=model_provider,
        retriever=retriever,
        do_research=do_research,
    )
    
    temp_files = []
    
    if transcript_file:
        transcript_path = temp_dir / f"transcript_{transcript_file.filename}"
        with transcript_path.open("wb") as f:
            content = await transcript_file.read()
            f.write(content)
        config.transcript_path = [str(transcript_path)]
        temp_files.append(str(transcript_path))
    
    if paper_file:
        paper_path = temp_dir / f"paper_{paper_file.filename}"
        with paper_path.open("wb") as f:
            content = await paper_file.read()
            f.write(content)
        config.paper_path = [str(paper_path)]
        temp_files.append(str(paper_path))
    
    if csv_file:
        csv_path = temp_dir / f"metadata_{csv_file.filename}"
        with csv_path.open("wb") as f:
            content = await csv_file.read()
            f.write(content)
        config.csv_path = str(csv_path)
        temp_files.append(str(csv_path))
    
    if video_file:
        video_path = temp_dir / f"video_{video_file.filename}"
        with video_path.open("wb") as f:
            content = await video_file.read()
            f.write(content)
        config.video_path = str(video_path)
        temp_files.append(str(video_path))
    
    # Store job information
    report_jobs[job_id] = {
        "status": "queued",
        "config": config,
        "progress": "File-based job queued for processing",
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "article_title": config.article_title,
        "model_provider": config.model_provider.value,
        "retriever": config.retriever.value,
        "temp_files": temp_files
    }
    
    # Start background task
    background_tasks.add_task(run_report_generation_task, job_id, config)
    
    return ReportResponse(
        job_id=job_id,
        status="queued",
        message="File-based report generation started successfully"
    )


@app.get("/api/reports/status/{job_id}", response_model=JobStatus)
async def get_report_status(job_id: str):
    """Get the status of a report generation job"""
    if job_id not in report_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = report_jobs[job_id]
    return JobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        result=job.get("result"),
        error=job.get("error"),
        created_at=job.get("created_at"),
        updated_at=job.get("updated_at")
    )


@app.get("/api/reports/jobs")
async def list_report_jobs(limit: int = 50, offset: int = 0):
    """List all report generation jobs with pagination"""
    jobs_list = []
    
    # Sort jobs by creation time (newest first)
    sorted_jobs = sorted(
        report_jobs.items(),
        key=lambda x: x[1].get("created_at", datetime.min),
        reverse=True
    )
    
    # Apply pagination
    paginated_jobs = sorted_jobs[offset:offset + limit]
    
    for job_id, job in paginated_jobs:
        jobs_list.append(JobSummary(
            job_id=job_id,
            status=job["status"],
            progress=job["progress"],
            article_title=job.get("article_title", "Unknown"),
            model_provider=job.get("model_provider", "unknown"),
            retriever=job.get("retriever", "unknown"),
            created_at=job.get("created_at", datetime.now()),
            has_result=job.get("result") is not None
        ))
    
    return {
        "jobs": jobs_list,
        "total": len(report_jobs),
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < len(report_jobs)
    }


@app.get("/api/reports/download/{job_id}/{filename}")
async def download_report_file(job_id: str, filename: str):
    """Download a generated report file"""
    if job_id not in report_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = report_jobs[job_id]
    if job["status"] != "completed" or not job.get("result"):
        raise HTTPException(status_code=400, detail="Job not completed or has no results")
    
    result = job["result"]
    
    # Find the requested file
    matching_files = [gf for gf in result["generated_files"] if os.path.basename(gf) == filename]
    if not matching_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = matching_files[0]
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )


@app.delete("/api/reports/jobs/{job_id}")
async def delete_report_job(job_id: str):
    """Delete a report generation job and clean up temporary files"""
    if job_id not in report_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = report_jobs[job_id]
    
    # Clean up temporary files
    temp_files = job.get("temp_files", [])
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            logging.warning(f"Failed to remove temporary file {temp_file}: {e}")
    
    # Remove job from memory
    del report_jobs[job_id]
    
    return {"message": f"Job {job_id} deleted successfully"}


@app.get("/api/config/models")
async def get_available_models():
    """Get available model providers and retrievers"""
    return {
        "model_providers": [provider.value for provider in ModelProvider],
        "retrievers": [retriever.value for retriever in RetrieverType],
        "time_ranges": [tr.value for tr in TimeRange]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_jobs": len([j for j in report_jobs.values() if j["status"] in ["queued", "running"]]),
        "total_jobs": len(report_jobs)
    }


# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logging.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )


if __name__ == "__main__":
    import uvicorn
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    uvicorn.run(
        "fastapi_integration_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 