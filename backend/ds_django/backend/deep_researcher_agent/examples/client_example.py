#!/usr/bin/env python3
"""
Example client for the Deep Report Generator API

This script demonstrates how to interact with the FastAPI server
to generate research reports programmatically.
"""

import asyncio
import time
import httpx
import json
from typing import Optional


class ReportGeneratorClient:
    """Client for interacting with the Deep Report Generator API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> dict:
        """Check if the API server is healthy"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def generate_report(
        self,
        topic: Optional[str] = None,
        transcript_content: Optional[str] = None,
        paper_content: Optional[str] = None,
        article_title: str = "StormReport",
        **kwargs
    ) -> dict:
        """
        Start a report generation job
        
        Args:
            topic: Research topic (if no content provided)
            transcript_content: Direct transcript content
            paper_content: Direct paper content
            article_title: Title for the generated article
            **kwargs: Additional configuration options
            
        Returns:
            Dict with job_id and status
        """
        payload = {
            "topic": topic,
            "transcript_content": transcript_content,
            "paper_content": paper_content,
            "article_title": article_title,
            **kwargs
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        response = await self.client.post(
            f"{self.base_url}/generate-report",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_job_status(self, job_id: str) -> dict:
        """Get the status of a report generation job"""
        response = await self.client.get(f"{self.base_url}/job/{job_id}")
        response.raise_for_status()
        return response.json()
    
    async def list_jobs(self) -> dict:
        """List all jobs"""
        response = await self.client.get(f"{self.base_url}/jobs")
        response.raise_for_status()
        return response.json()
    
    async def download_file(self, job_id: str, filename: str, save_path: str):
        """Download a generated file"""
        response = await self.client.get(f"{self.base_url}/download/{job_id}/{filename}")
        response.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(response.content)
    
    async def wait_for_completion(
        self, 
        job_id: str, 
        timeout: int = 3600,
        poll_interval: int = 10
    ) -> dict:
        """
        Wait for a job to complete
        
        Args:
            job_id: Job ID to wait for
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check status in seconds
            
        Returns:
            Final job status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.get_job_status(job_id)
            
            if status["status"] in ["completed", "failed"]:
                return status
            
            print(f"Job {job_id} status: {status['status']} - {status['progress']}")
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


async def example_simple_topic_generation():
    """Example: Generate a report from a simple topic"""
    
    client = ReportGeneratorClient()
    
    try:
        # Check server health
        health = await client.health_check()
        print(f"Server health: {health}")
        
        # Start report generation
        print("\n--- Generating report for 'Quantum Computing Applications' ---")
        job = await client.generate_report(
            topic="Quantum Computing Applications in Cryptography",
            article_title="Quantum Computing and Cryptography",
            do_research=True,
            max_conv_turn=2,  # Reduce for faster generation
            max_perspective=2
        )
        
        print(f"Job started: {job}")
        job_id = job["job_id"]
        
        # Wait for completion
        print("Waiting for completion...")
        final_status = await client.wait_for_completion(job_id, timeout=1800)  # 30 minutes
        
        if final_status["status"] == "completed":
            print("\n--- Report generation completed! ---")
            result = final_status["result"]
            print(f"Article title: {result['article_title']}")
            print(f"Output directory: {result['output_directory']}")
            print(f"Generated files: {result['generated_files']}")
            
            # Download the main report file
            if result["generated_files"]:
                for file_path in result["generated_files"]:
                    filename = file_path.split("/")[-1]  # Get just the filename
                    if filename.endswith(".md"):
                        local_path = f"downloaded_{filename}"
                        await client.download_file(job_id, filename, local_path)
                        print(f"Downloaded: {local_path}")
                        break
        else:
            print(f"\n--- Report generation failed ---")
            print(f"Error: {final_status.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()


async def example_transcript_generation():
    """Example: Generate a report from transcript content"""
    
    client = ReportGeneratorClient()
    
    # Sample transcript content
    transcript_content = """
    Welcome to today's discussion on artificial intelligence in healthcare. 
    
    Dr. Smith: Thank you for joining us. Today we're exploring how AI is revolutionizing 
    medical diagnosis and treatment. Machine learning algorithms can now analyze medical 
    images with accuracy that rivals human specialists.
    
    Dr. Johnson: That's absolutely right. In radiology, for instance, AI systems can 
    detect early-stage cancers in mammograms and CT scans that might be missed by human 
    radiologists. The sensitivity and specificity rates are quite impressive.
    
    Dr. Smith: And it's not just imaging. Natural language processing is being used to 
    analyze electronic health records, extracting valuable insights from unstructured 
    clinical notes. This helps with risk prediction and personalized treatment recommendations.
    
    Dr. Johnson: The potential for drug discovery is enormous too. AI can analyze 
    molecular structures and predict how different compounds might interact with 
    biological targets, significantly accelerating the research process.
    
    Host: What about the challenges and ethical considerations?
    
    Dr. Smith: Privacy and data security are paramount. We need robust frameworks 
    to ensure patient data is protected while still enabling meaningful research.
    
    Dr. Johnson: Bias in AI algorithms is another critical concern. If training 
    data isn't representative, AI systems might perpetuate or amplify existing 
    healthcare disparities.
    """
    
    try:
        print("\n--- Generating report from transcript content ---")
        job = await client.generate_report(
            transcript_content=transcript_content,
            article_title="AI in Healthcare: Opportunities and Challenges",
            do_research=True,
            max_conv_turn=2,
            max_perspective=2
        )
        
        print(f"Job started: {job}")
        job_id = job["job_id"]
        
        # Wait for completion
        print("Waiting for completion...")
        final_status = await client.wait_for_completion(job_id, timeout=1800)
        
        if final_status["status"] == "completed":
            print("\n--- Report generation completed! ---")
            result = final_status["result"]
            print(f"Article title: {result['article_title']}")
            print(f"Generated files: {len(result['generated_files'])} files")
        else:
            print(f"\n--- Report generation failed ---")
            print(f"Error: {final_status.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()


async def example_list_and_manage_jobs():
    """Example: List and manage jobs"""
    
    client = ReportGeneratorClient()
    
    try:
        # List all jobs
        jobs = await client.list_jobs()
        print(f"\n--- All Jobs ({jobs['total']}) ---")
        
        for job in jobs["jobs"]:
            print(f"Job ID: {job['job_id']}")
            print(f"Status: {job['status']}")
            print(f"Progress: {job['progress']}")
            print(f"Has Result: {job['has_result']}")
            print("---")
    
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.close()


async def main():
    """Main example function"""
    print("Deep Report Generator API Client Examples")
    print("=" * 50)
    
    # Choose which example to run
    examples = {
        "1": ("Simple Topic Generation", example_simple_topic_generation),
        "2": ("Transcript Generation", example_transcript_generation),
        "3": ("List and Manage Jobs", example_list_and_manage_jobs),
    }
    
    print("\nAvailable examples:")
    for key, (name, _) in examples.items():
        print(f"{key}. {name}")
    
    choice = input("\nEnter example number (1-3) or 'all' to run all: ").strip()
    
    if choice.lower() == "all":
        for name, func in examples.values():
            print(f"\n{'='*20} {name} {'='*20}")
            await func()
    elif choice in examples:
        name, func = examples[choice]
        print(f"\n{'='*20} {name} {'='*20}")
        await func()
    else:
        print("Invalid choice. Running simple topic generation...")
        await example_simple_topic_generation()


if __name__ == "__main__":
    # Run the example
    asyncio.run(main()) 