import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { config } from "@/config";
import studioService from "@/features/notebook/services/StudioService";

class AbortError extends Error {
  constructor() {
    super('AbortError');
    this.name = 'AbortError';
  }
}

export const useJobStatus = (
  jobId: string | null, 
  onComplete: (result: any) => void, 
  onError: (error: string) => void, 
  notebookId: string, 
  jobType: string = 'podcast'
) => {
  // Validate required parameters
  if (jobId && !notebookId) {
    throw new Error('notebookId is required when jobId is provided');
  }
  
  const [status, setStatus] = useState<string | null>(null);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const ctrlRef = useRef<AbortController | null>(null); // AbortController ref
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const isConnectingRef = useRef(false);
  const jobCompletedRef = useRef(false); // Track if job is completed
  
  // Store callbacks in refs to avoid recreating connections when they change
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const currentJobIdRef = useRef(jobId);
  const currentNotebookIdRef = useRef(notebookId);

  // Update refs when props change
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    currentJobIdRef.current = jobId;
    currentNotebookIdRef.current = notebookId;
    // Reset completion flag when job ID changes
    if (jobId !== currentJobIdRef.current) {
      jobCompletedRef.current = false;
    }
  }, [jobId, notebookId]);

  const connectEventSource = useCallback(() => {
    if (!currentJobIdRef.current || jobCompletedRef.current || isConnectingRef.current) {
      console.log('Skipping SSE connection:', { 
        hasJobId: !!currentJobIdRef.current, 
        isCompleted: jobCompletedRef.current, 
        isConnecting: isConnectingRef.current 
      });
      return;
    }

    isConnectingRef.current = true;
    console.log('Starting SSE connection for job:', currentJobIdRef.current, 'type:', jobType);
    
    // Create a new AbortController for this connection attempt
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    
    try {
      // Use the appropriate API service method to get the correct SSE URL
      const sseUrl = jobType === 'report'
        ? studioService.getReportJobStatusStreamUrl(currentJobIdRef.current, currentNotebookIdRef.current)
        : studioService.getPodcastJobStatusStreamUrl(currentJobIdRef.current, currentNotebookIdRef.current);
      
      console.log(`Connecting to ${jobType} SSE:`, sseUrl);
      
      fetchEventSource(sseUrl, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
        },
        credentials: 'include', // Use session-based authentication
        signal: ctrl.signal,

        onopen: async (response) => {
          if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
            console.log('SSE Connection opened successfully');
            setIsConnected(true);
            setConnectionError(null);
            reconnectAttemptsRef.current = 0;
            isConnectingRef.current = false;
          } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            console.error('Client-side error opening SSE connection:', response.status, response.statusText);
            setConnectionError('Client-side error connecting to server.');
            throw new AbortError(); // Don't retry on client errors
          } else {
            console.error('Server-side error opening SSE connection:', response.status, response.statusText);
            setConnectionError('Server-side error connecting.');
            // Let the default retry mechanism handle server errors
          }
        },

        onmessage: (event) => {
          try {
            const parsedEvent = JSON.parse(event.data);
            console.log('Received SSE data:', parsedEvent);

            // Check for control messages
            if (parsedEvent.type === 'stream_closed' || !parsedEvent.data) {
              console.log('Stream closed by server.');
              jobCompletedRef.current = true;
              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
              return;
            }
            
            const jobData = parsedEvent.data;

            setStatus(jobData.status);
            setProgress(jobData.progress);
            
            // Debug logging for progress updates
            if (jobData.progress) {
              console.log('Job progress update:', jobData.progress);
            }
            
            if (jobData.status === 'completed') {
              jobCompletedRef.current = true;
              
              const resultData = {
                jobId: jobData.job_id,
                ...jobData
              };
              
              setResult(resultData);
              
              if (onCompleteRef.current) {
                onCompleteRef.current(resultData);
              }
              
              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
              
            } else if (jobData.status === 'failed') {
              jobCompletedRef.current = true;
              const errorMsg = jobData.error || 'Job failed';
              setError(errorMsg);
              
              if (onErrorRef.current) {
                onErrorRef.current(errorMsg);
              }
              
              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
              
            } else if (jobData.status === 'cancelled') {
              jobCompletedRef.current = true;
              setError('Job was cancelled');
              
              if (onErrorRef.current) {
                onErrorRef.current('Job was cancelled');
              }

              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
            }
          } catch (error) {
            console.error('Error parsing SSE data:', error);
          }
        },

        onerror: (err) => {
          console.error('SSE Connection error:', err);
          setIsConnected(false);
          isConnectingRef.current = false;
          
          if (err.name === 'AbortError') {
            console.log('SSE connection aborted intentionally.');
            throw err; // Prevent reconnection
          }
          
          if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
            setConnectionError('Unable to connect to server. Please refresh the page.');
            console.error('Max reconnection attempts reached.');
            throw err; // Prevent further retries
          }

          reconnectAttemptsRef.current++;
          setConnectionError(`Connection lost, reconnecting... (${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
        },
        
        onclose: () => {
          console.log('SSE connection closed.');
          setIsConnected(false);
          isConnectingRef.current = false;
        }
      });

    } catch (error) {
      console.error('Failed to create EventSource:', error);
      setConnectionError('Failed to connect to server');
      isConnectingRef.current = false;
    }

  }, [jobType]);

  // Function to cancel job
  const cancel = useCallback(async () => {
    if (!currentJobIdRef.current || !currentNotebookIdRef.current) return false;
    
    try {
      const success = jobType === 'report'
        ? await studioService.cancelReportJob(currentJobIdRef.current, currentNotebookIdRef.current)
        : await studioService.cancelPodcastJob(currentJobIdRef.current, currentNotebookIdRef.current);
      
      if (success) {
        jobCompletedRef.current = true;
        setStatus('cancelled');
        setError('Job cancelled');
        
        if (ctrlRef.current) {
          ctrlRef.current.abort();
          ctrlRef.current = null;
        }
        setIsConnected(false);
      }
      
      return success;
    } catch (error) {
      console.error('Error cancelling job:', error);
      return false;
    }
  }, [jobType]);

  // Function to disconnect from current job
  const disconnect = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('Disconnecting from job status updates');
    }
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (ctrlRef.current) {
      ctrlRef.current.abort();
      ctrlRef.current = null;
    }
    
    setIsConnected(false);
    setStatus(null);
    setProgress('');
    setResult(null);
    setError(null);
    setConnectionError(null);
    reconnectAttemptsRef.current = 0;
    isConnectingRef.current = false;
    jobCompletedRef.current = false;
  }, []);

  // Effect to handle job ID changes
  useEffect(() => {
    if (jobId && notebookId) {
      // Reset state for new job
      disconnect(); // Ensure any previous connection is closed
      
      // Start SSE connection
      connectEventSource();
    } else {
      // Disconnect when no job ID
      disconnect();
    }
    
    return () => {
      disconnect(); // Cleanup on unmount
    };
  }, [jobId, notebookId, connectEventSource, disconnect]);

  return { status, progress, result, error, isConnected, connectionError, cancel, disconnect };
};