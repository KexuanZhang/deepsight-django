import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import asyncio
import uuid
import logging

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add the deep-researcher-agent directory to Python path
# Adjust the path based on your actual directory structure
CURRENT_DIR = Path(__file__).parent
DEEP_RESEARCHER_DIR = CURRENT_DIR.parent / "deep-researcher-agent"
sys.path.insert(0, str(DEEP_RESEARCHER_DIR))

# Now import the report generator components
from deep_report_generator_api import (
    DeepReportGenerator,
    ReportGenerationConfig,
    ReportGenerationResult,
    RetrieverType,
    TimeRange,
    generate_report_from_config
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state for tracking report generation jobs
report_jobs: Dict[str, Dict] = {}

# Initialize the report generator (you might want to do this in a startup event)
def get_report_generator():
    """Get or create report generator instance"""
    secrets_path = DEEP_RESEARCHER_DIR / "secrets.toml"
    return DeepReportGenerator(secrets_path=str(secrets_path))


# Pydantic models for the API
class ReportRequest(BaseModel):
    """Request model for report generation"""
    topic: Optional[str] = Field(None, description="Research topic")
    transcript_content: Optional[str] = Field(None, description="Transcript content")
    paper_content: Optional[str] = Field(None, description="Paper content")
    article_title: str = Field("Research Report", description="Article title")
    
    # Configuration options
    retriever: RetrieverType = Field(RetrieverType.TAVILY, description="Search engine")
    do_research: bool = Field(True, description="Perform research")
    max_conv_turn: int = Field(2, ge=1, le=5, description="Max conversation turns")
    max_perspective: int = Field(2, ge=1, le=5, description="Max perspectives")


class ReportResponse(BaseModel):
    """Response model for report generation"""
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Job status response"""
    job_id: str
    status: str
    progress: str
    result: Optional[Dict] = None
    error: Optional[str] = None


def run_report_generation_task(job_id: str, config: ReportGenerationConfig):
    """Background task to run report generation"""
    try:
        report_jobs[job_id]["status"] = "running"
        report_jobs[job_id]["progress"] = "Starting report generation..."
        
        # Generate the report
        result = generate_report_from_config(config, secrets_path=str(DEEP_RESEARCHER_DIR / "secrets.toml"))
        
        if result.success:
            report_jobs[job_id]["status"] = "completed"
            report_jobs[job_id]["result"] = {
                "article_title": result.article_title,
                "output_directory": result.output_directory,
                "generated_files": result.generated_files,
                "processing_logs": result.processing_logs
            }
            report_jobs[job_id]["progress"] = "Report generation completed successfully"
        else:
            report_jobs[job_id]["status"] = "failed"
            report_jobs[job_id]["error"] = result.error_message
            report_jobs[job_id]["progress"] = "Report generation failed"
            
    except Exception as e:
        logger.exception(f"Report generation failed for job {job_id}")
        report_jobs[job_id]["status"] = "failed"
        report_jobs[job_id]["error"] = str(e)
        report_jobs[job_id]["progress"] = "Report generation failed with exception"


# FastAPI app instance (this would be in your main.py)
app = FastAPI(title="Your Backend API with Report Generator")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/reports/generate", response_model=ReportResponse)
async def generate_research_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks
):
    """Generate a research report"""
    
    # Validate input
    if not request.topic and not request.transcript_content and not request.paper_content:
        raise HTTPException(
            status_code=400,
            detail="Either topic, transcript_content, or paper_content must be provided"
        )
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Create configuration
    config = ReportGenerationConfig(
        topic=request.topic,
        article_title=request.article_title,
        output_dir=str(DEEP_RESEARCHER_DIR / "results" / "api"),
        retriever=request.retriever,
        do_research=request.do_research,
        max_conv_turn=request.max_conv_turn,
        max_perspective=request.max_perspective,
        temperature=0.2,
        top_p=0.4,
    )
    
    # Handle content inputs
    if request.transcript_content:
        # Save to temporary file
        temp_dir = DEEP_RESEARCHER_DIR / "results" / "api" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        transcript_file = temp_dir / f"transcript_{job_id}.txt"
        transcript_file.write_text(request.transcript_content, encoding='utf-8')
        config.transcript_path = [str(transcript_file)]
    
    if request.paper_content:
        # Save to temporary file
        temp_dir = DEEP_RESEARCHER_DIR / "results" / "api" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        paper_file = temp_dir / f"paper_{job_id}.md"
        paper_file.write_text(request.paper_content, encoding='utf-8')
        config.paper_path = [str(paper_file)]
    
    # Initialize job tracking
    report_jobs[job_id] = {
        "status": "queued",
        "config": config,
        "progress": "Job queued for processing",
        "result": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_report_generation_task, job_id, config)
    
    return ReportResponse(
        job_id=job_id,
        status="queued",
        message="Report generation started successfully"
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
        error=job.get("error")
    )


@app.get("/api/reports/jobs")
async def list_report_jobs():
    """List all report generation jobs"""
    
    jobs_summary = []
    for job_id, job in report_jobs.items():
        jobs_summary.append({
            "job_id": job_id,
            "status": job["status"],
            "progress": job["progress"],
            "has_result": job.get("result") is not None
        })
    
    return {"jobs": jobs_summary, "total": len(jobs_summary)}


@app.get("/api/reports/download/{job_id}/{filename}")
async def download_report_file(job_id: str, filename: str):
    """Download a generated report file"""
    from fastapi.responses import FileResponse
    
    if job_id not in report_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = report_jobs[job_id]
    if job["status"] != "completed" or not job.get("result"):
        raise HTTPException(status_code=400, detail="Job not completed or has no results")
    
    result = job["result"]
    
    # Find the file in generated files
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


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "backend with report generator"}


# Example of how to integrate into your existing main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 