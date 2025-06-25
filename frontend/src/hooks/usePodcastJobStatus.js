import { useState, useEffect, useRef, useCallback } from 'react';
import { config } from '../config';
import apiService from '../lib/api';

export const usePodcastJobStatus = (jobId, onComplete, onError, notebookId) => {
  // Validate required parameters
  if (jobId && !notebookId) {
    throw new Error('notebookId is required when jobId is provided');
  }
  
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

  // Fallback polling mechanism
  const startPolling = useCallback(() => {
    // Don't start polling if job is already completed
    if (jobCompletedRef.current) {
      console.log('Job already completed, skipping polling');
      return;
    }

    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    console.log('Starting fallback polling for podcast job:', jobId);
    
    pollIntervalRef.current = setInterval(async () => {
      if (!currentJobIdRef.current || jobCompletedRef.current) return;

      try {
        // Use the new API service method with notebook support
        const data = await apiService.getPodcastJobStatus(currentJobIdRef.current, currentNotebookIdRef.current);
        
        setStatus(data.status);
        setProgress(data.progress || 'Processing...');
        setConnectionError(null);
        
        if (data.status === 'completed' && (data.audio_file || data.audio_file_url)) {
          jobCompletedRef.current = true; // Mark job as completed
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
          jobCompletedRef.current = true; // Mark job as completed (with error)
          const errorMsg = data.error_message || 'Job failed';
          setError(errorMsg);
          
          if (onErrorRef.current) {
            onErrorRef.current(errorMsg);
          }
          
          // Stop polling on error
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        } else if (data.status === 'cancelled') {
          jobCompletedRef.current = true; // Mark job as completed (cancelled)
          setError('Cancelled');
          
          // Stop polling on cancellation
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
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
    if (!currentJobIdRef.current || isConnectingRef.current || jobCompletedRef.current) {
      if (jobCompletedRef.current) {
        console.log('Job already completed, skipping SSE connection');
      }
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
      
      // Use the new API service method to get the correct SSE URL
      const sseUrl = apiService.getPodcastJobStatusStreamUrl(currentJobIdRef.current, currentNotebookIdRef.current);
      
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
              jobCompletedRef.current = true; // Mark job as completed
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
              
              // Close the connection after completion
              eventSource.close();
              setIsConnected(false);
            } else if (jobData.status === 'error') {
              jobCompletedRef.current = true; // Mark job as completed (with error)
              const errorMsg = jobData.error_message || 'Job failed';
              setError(errorMsg);
              
              if (onErrorRef.current) {
                onErrorRef.current(errorMsg);
              }
              
              // Close the connection after error
              eventSource.close();
              setIsConnected(false);
            } else if (jobData.status === 'cancelled') {
              jobCompletedRef.current = true; // Mark job as completed (cancelled)
              setError('Cancelled');
              
              // Close the connection after cancellation
              eventSource.close();
              setIsConnected(false);
            }
          } else if (data.type === 'stream_closed') {
            console.log('SSE stream closed by server');
            eventSource.close();
            setIsConnected(false);
            return; // Don't treat this as an error
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
        console.log('SSE connection error. Job completed?', jobCompletedRef.current);
        setIsConnected(false);
        isConnectingRef.current = false;
        
        // If the job is already completed, don't treat connection closure as an error
        if (jobCompletedRef.current) {
          console.log('SSE connection closed after job completion - this is expected');
          return;
        }
        
        // Suppress the error if the event source is already closed (readyState === 2)
        // This happens when the server closes the connection normally after job completion
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('SSE connection already closed, checking if job completed');
        }
        
        // Check the EventSource readyState to determine if this is a connection error or normal closure
        if (eventSource.readyState === EventSource.CLOSED) {
          console.log('SSE connection was closed normally');
          // Check if job completed while we weren't looking
          if (currentJobIdRef.current && currentNotebookIdRef.current) {
            // Do a single status check to see if job completed
            fetch(`${config.API_BASE_URL}/notebooks/${currentNotebookIdRef.current}/jobs/${currentJobIdRef.current}/`, {
              credentials: 'include'
            })
            .then(response => response.ok ? response.json() : null)
            .then(data => {
              if (data && ['completed', 'error', 'cancelled'].includes(data.status)) {
                jobCompletedRef.current = true;
                console.log('Job completed while SSE was disconnected');
                
                if (data.status === 'completed') {
                  const resultData = {
                    jobId: data.job_id,
                    status: data.status,
                    audioUrl: data.audio_file || data.audio_file_url,
                    title: data.title,
                    progress: data.progress
                  };
                  setResult(resultData);
                  setStatus(data.status);
                  setProgress(data.progress || 'Completed');
                  
                  if (onCompleteRef.current) {
                    onCompleteRef.current(resultData);
                  }
                } else if (data.status === 'error') {
                  const errorMsg = data.error_message || 'Job failed';
                  setError(errorMsg);
                  setStatus(data.status);
                  
                  if (onErrorRef.current) {
                    onErrorRef.current(errorMsg);
                  }
                }
              } else {
                // Job is still running, start polling fallback
                console.log('Job still running, starting polling fallback');
                startPolling();
              }
            })
            .catch(err => {
              console.error('Error checking job status after SSE closure:', err);
              startPolling(); // Fallback to polling
            });
          }
          return;
        }
        
        console.error('SSE error (will attempt reconnect):', error);
        
        // Start polling as fallback
        startPolling();
        
        // Attempt to reconnect with exponential backoff only if job is not completed
        if (reconnectAttemptsRef.current < maxReconnectAttempts && !jobCompletedRef.current) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 15000);
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            if (!jobCompletedRef.current) {
              connectEventSource();
            }
          }, delay);
        } else {
          console.log('Max reconnection attempts reached or job completed, using polling fallback');
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
    if (!currentJobIdRef.current || !currentNotebookIdRef.current) {
      console.error('Cannot cancel job: missing jobId or notebookId');
      return false;
    }

    try {
      // Helper to get CSRF token from cookie
      const getCookie = (name) => {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        return match ? decodeURIComponent(match[2]) : null;
      };

      const response = await fetch(`${config.API_BASE_URL}/notebooks/${currentNotebookIdRef.current}/jobs/${currentJobIdRef.current}/cancel/`, {
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
        const errorText = await response.text();
        console.error('Failed to cancel job:', response.status, errorText);
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
      jobCompletedRef.current = false; // Reset completion flag for new job
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
      jobCompletedRef.current = false; // Reset completion flag
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