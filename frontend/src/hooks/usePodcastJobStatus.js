import { useState, useEffect, useRef, useCallback } from 'react';
import { config } from '../config';

export const usePodcastJobStatus = (jobId, onComplete, onError) => {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const pollIntervalRef = useRef(null);
  const isConnectingRef = useRef(false);
  
  // Store callbacks in refs to avoid recreating connections when they change
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const currentJobIdRef = useRef(jobId);

  // Update refs when props change
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    currentJobIdRef.current = jobId;
  }, [jobId]);

  // Fallback polling mechanism
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    console.log('Starting fallback polling for podcast job:', jobId);
    
    pollIntervalRef.current = setInterval(async () => {
      if (!currentJobIdRef.current) return;

      try {
        const response = await fetch(`${config.API_BASE_URL}/podcasts/jobs/${currentJobIdRef.current}/`, {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          
          setStatus(data.status);
          setProgress(data.progress || 'Processing...');
          setConnectionError(null);
          
          if (data.status === 'completed' && (data.audio_file || data.audio_file_url)) {
            const resultData = {
              jobId: data.job_id,
              status: data.status,
              audioUrl: data.audio_file || data.audio_file_url,
              title: data.title,
              progress: data.progress
            };
            setResult(resultData);
            
            if (onCompleteRef.current) {
              onCompleteRef.current(resultData);
            }
            
            // Stop polling on completion
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          } else if (data.status === 'error') {
            const errorMsg = data.error_message || 'Job failed';
            setError(errorMsg);
            
            if (onErrorRef.current) {
              onErrorRef.current(errorMsg);
            }
            
            // Stop polling on error
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        } else {
          console.error('Failed to fetch job status:', response.status);
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        setConnectionError('Failed to check job status');
      }
    }, 3000); // Poll every 3 seconds
  }, [jobId]);

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const connectEventSource = useCallback(() => {
    if (!currentJobIdRef.current || isConnectingRef.current) {
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    isConnectingRef.current = true;
    console.log('connectEventSource called for job:', currentJobIdRef.current);

    // Clear any existing polling
    stopPolling();

    try {
      console.log('Starting new SSE connection for job:', currentJobIdRef.current);
      
      const sseUrl = `${config.API_BASE_URL}/podcasts/stream/job-status/${currentJobIdRef.current}`;
      
      console.log('Connecting to SSE:', sseUrl);
      
      const eventSource = new EventSource(sseUrl, {
        withCredentials: true
      });
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('SSE connection opened for job:', currentJobIdRef.current);
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        isConnectingRef.current = false;
      };

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Received SSE message:', data);

          if (data.type === 'job_status' && data.data) {
            const jobData = data.data;
            
            setStatus(jobData.status);
            setProgress(jobData.progress || 'Processing...');
            setError(jobData.error_message || null);

            if (jobData.status === 'completed') {
              const resultData = {
                jobId: jobData.job_id,
                status: jobData.status,
                audioUrl: jobData.audio_file_url,
                title: jobData.title,
                progress: jobData.progress
              };
              setResult(resultData);
              
              if (onCompleteRef.current) {
                onCompleteRef.current(resultData);
              }
            } else if (jobData.status === 'error') {
              const errorMsg = jobData.error_message || 'Job failed';
              setError(errorMsg);
              
              if (onErrorRef.current) {
                onErrorRef.current(errorMsg);
              }
            }
          } else if (data.type === 'error') {
            console.error('SSE error message:', data.message);
            setError(data.message);
            if (onErrorRef.current) {
              onErrorRef.current(data.message);
            }
          }
        } catch (error) {
          console.error('Error parsing SSE message:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE error:', error);
        setIsConnected(false);
        isConnectingRef.current = false;
        
        // Start polling as fallback
        startPolling();
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 15000);
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connectEventSource();
          }, delay);
        } else {
          console.log('Max reconnection attempts reached, using polling fallback');
          setConnectionError('Connection failed, using fallback mode');
        }
      };

    } catch (error) {
      console.error('Error creating SSE connection:', error);
      isConnectingRef.current = false;
      setConnectionError('Failed to establish connection');
      
      // Fallback to polling
      startPolling();
    }
  }, [stopPolling, startPolling]);

  // Function to cancel job
  const cancelJob = useCallback(async () => {
    if (!currentJobIdRef.current) {
      return false;
    }

    try {
      // Helper to get CSRF token from cookie
      const getCookie = (name) => {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        return match ? decodeURIComponent(match[2]) : null;
      };

      const response = await fetch(`${config.API_BASE_URL}/podcasts/jobs/${currentJobIdRef.current}/cancel/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken'),
        }
      });

      if (response.ok) {
        console.log('Job cancellation request sent successfully');
        return true;
      } else {
        console.error('Failed to cancel job:', response.status);
        return false;
      }
    } catch (error) {
      console.error('Error cancelling job:', error);
      return false;
    }
  }, []);

  // Effect to manage connection based on jobId
  useEffect(() => {
    if (jobId) {
      console.log('Job ID changed, connecting for:', jobId);
      connectEventSource();
    } else {
      console.log('No job ID, cleaning up connections');
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      stopPolling();
      setIsConnected(false);
      setStatus(null);
      setProgress('');
      setResult(null);
      setError(null);
      setConnectionError(null);
    }

    // Cleanup function
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      stopPolling();
      isConnectingRef.current = false;
    };
  }, [jobId, connectEventSource, stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      stopPolling();
    };
  }, [stopPolling]);

  return {
    status,
    progress,
    result,
    error,
    isConnected,
    connectionError,
    cancelJob
  };
};