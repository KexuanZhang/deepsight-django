#!/usr/bin/env python3
"""
Real-time job monitoring for Deep Report Generator
"""

import asyncio
import httpx
import json
from datetime import datetime
import sys

import os

BASE_URL = (
    f"http://{os.getenv('HOST_IP', 'localhost')}:{os.getenv('BACKEND_PORT', '8000')}"
)


async def monitor_jobs():
    """Monitor all active jobs in real-time"""
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Get all jobs
                response = await client.get(f"{BASE_URL}/api/reports/jobs?limit=20")
                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])

                    # Clear screen
                    print("\033[2J\033[H")
                    print("🔍 Deep Report Generator - Job Monitor")
                    print("=" * 60)
                    print(
                        f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    print(f"Total Jobs: {data.get('total', 0)}")
                    print()

                    # Show active jobs
                    active_jobs = [
                        j for j in jobs if j["status"] in ["queued", "running"]
                    ]
                    if active_jobs:
                        print("🚀 ACTIVE JOBS:")
                        for job in active_jobs:
                            status_emoji = "⏳" if job["status"] == "queued" else "🔄"
                            print(
                                f"  {status_emoji} {job['job_id'][:8]}... | {job['status'].upper()} | {job['article_title']}"
                            )
                            print(
                                f"     Model: {job['model_provider']} | Retriever: {job['retriever']}"
                            )
                        print()

                    # Show recent completed jobs
                    completed_jobs = [j for j in jobs if j["status"] == "completed"][:5]
                    if completed_jobs:
                        print("✅ RECENT COMPLETED:")
                        for job in completed_jobs:
                            print(
                                f"  ✅ {job['job_id'][:8]}... | {job['article_title']}"
                            )
                        print()

                    # Show any failed jobs
                    failed_jobs = [j for j in jobs if j["status"] == "failed"][:3]
                    if failed_jobs:
                        print("❌ FAILED JOBS:")
                        for job in failed_jobs:
                            print(
                                f"  ❌ {job['job_id'][:8]}... | {job['article_title']}"
                            )
                        print()

                    if not active_jobs and not completed_jobs and not failed_jobs:
                        print("📭 No jobs found")

                    print("\nPress Ctrl+C to exit")

                else:
                    print(f"❌ Failed to fetch jobs: {response.status_code}")

            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

            await asyncio.sleep(5)  # Update every 5 seconds


async def monitor_specific_job(job_id: str):
    """Monitor a specific job until completion"""
    async with httpx.AsyncClient() as client:
        print(f"🔍 Monitoring job: {job_id}")
        print("=" * 40)

        while True:
            try:
                response = await client.get(f"{BASE_URL}/api/reports/status/{job_id}")
                if response.status_code == 200:
                    status = response.json()

                    print(
                        f"\r{datetime.now().strftime('%H:%M:%S')} | "
                        f"Status: {status['status'].upper()} | "
                        f"Progress: {status['progress']}",
                        end="",
                        flush=True,
                    )

                    if status["status"] in ["completed", "failed"]:
                        print()  # New line
                        if status["status"] == "completed":
                            print("✅ Job completed successfully!")
                            if status.get("result"):
                                result = status["result"]
                                print(
                                    f"📁 Output directory: {result['output_directory']}"
                                )
                                print(
                                    f"📄 Generated files: {len(result['generated_files'])}"
                                )
                                for file_path in result["generated_files"]:
                                    print(f"  - {file_path}")
                        else:
                            print("❌ Job failed!")
                            if status.get("error"):
                                print(f"Error: {status['error']}")
                        break

                else:
                    print(f"❌ Failed to get status: {response.status_code}")
                    break

            except KeyboardInterrupt:
                print("\n👋 Monitoring stopped")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                break

            await asyncio.sleep(2)  # Update every 2 seconds


if __name__ == "__main__":
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
        asyncio.run(monitor_specific_job(job_id))
    else:
        asyncio.run(monitor_jobs())
