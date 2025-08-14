// Simple job storage utility for persisting generation job data
export class JobStorage {
  saveJob(jobId: string, jobData: any): void {
    const key = `studio_job_${jobId}`;
    localStorage.setItem(key, JSON.stringify(jobData));
  }

  getJob(jobId: string): any {
    const key = `studio_job_${jobId}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  }

  clearJob(jobId: string): void {
    const key = `studio_job_${jobId}`;
    localStorage.removeItem(key);
  }
}

export const jobStorage = new JobStorage();