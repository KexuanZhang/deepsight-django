import { useState, useEffect, useRef } from 'react';

export const useJobStatus = (jobId, onComplete, onError) => {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const maxReconnectAttempts = 10; // Increased from 5
  const reconnectAttemptsRef = useRef(0);
  const pollIntervalRef = useRef(null);
  
  // Store latest values in refs to avoid closure issues
  const latestResultRef = useRef(null);
  const latestErrorRef = useRef(null);

  // Update refs when state changes
  useEffect(() => {
    latestResultRef.current = result;
  }, [result]);

  useEffect(() => {
    latestErrorRef.current = error;
  }, [error]);

  // Fallback polling mechanism
  const startPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    pollIntervalRef.current = setInterval(async () => {
      if (!jobId) return;

      try {
        const response = await fetch(`/api/reports/status/${jobId}`);
        if (response.ok) {
          const data = await response.json();
          
          setStatus(data.status);
          setProgress(data.progress || 'Processing...');
          setConnectionError(null);
          
          if (data.result) {
            setResult(data.result);
          }
          if (data.error) {
            setError(data.error);
          }

          // Check if job is complete
          if (data.status === 'completed' && onComplete) {
            clearInterval(pollIntervalRef.current);
            const finalResult = latestResultRef.current || data.result;
            onComplete(finalResult);
          } else if (data.status === 'failed' && onError) {
            clearInterval(pollIntervalRef.current);
            const finalError = latestErrorRef.current || data.error || 'Job failed';
            onError(finalError);
          } else if (data.status === 'cancelled') {
            clearInterval(pollIntervalRef.current);
            // Don't call onError for cancelled jobs, just stop monitoring
          }
        } else {
          throw new Error(`HTTP ${response.status}`);
        }
      } catch (error) {
        console.error('Polling error:', error);
        setConnectionError('Using fallback connection mode');
      }
    }, 2000); // Poll every 2 seconds
  };

  const connectToStream = () => {
    if (!jobId) return;
    
    // Clean up existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource(`/api/reports/status/${jobId}/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('Connected to job status stream:', jobId);
        setIsConnected(true);
        setError(null);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        
        // Stop polling since SSE is working
        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
        }
      };

      eventSource.addEventListener('status_update', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Job status update:', data);
          
          setStatus(data.status);
          setProgress(data.progress);
          
          if (data.result) {
            setResult(data.result);
          }
          if (data.error) {
            setError(data.error);
          }
        } catch (parseError) {
          console.error('Error parsing status update:', parseError);
        }
      });

      eventSource.addEventListener('job_finished', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('Job finished:', data);
          
          // Close connection first
          eventSource.close();
          setIsConnected(false);
          
          // Update final state
          setStatus(data.status);
          
          // Trigger callbacks based on the status
          if (data.status === 'completed' && onComplete) {
            const finalResult = latestResultRef.current || (data.result ? data.result : null);
            onComplete(finalResult);
          } else if (data.status === 'failed' && onError) {
            const finalError = latestErrorRef.current || (data.error ? data.error : 'Job failed');
            onError(finalError);
          } else if (data.status === 'cancelled') {
            // Don't call onError for cancelled jobs, just stop monitoring
          }
          
        } catch (parseError) {
          console.error('Error parsing job finished event:', parseError);
        }
      });

      eventSource.addEventListener('error', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.error('SSE Error:', data.error);
          setError(data.error);
          if (onError) onError(data.error);
        } catch (parseError) {
          console.error('Error parsing error event:', parseError);
        }
      });

      eventSource.onerror = (event) => {
        console.error('EventSource failed:', event);
        setIsConnected(false);
        
        // Start polling immediately as fallback
        setConnectionError('Connection lost, using fallback mode');
        startPolling();
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(Math.pow(2, reconnectAttemptsRef.current) * 1000, 30000); // Max 30 seconds
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectToStream();
          }, delay);
        } else {
          console.error('Max reconnection attempts reached, falling back to polling');
          setConnectionError('Using fallback connection (polling)');
        }
      };

    } catch (connectionError) {
      console.error('Failed to establish SSE connection:', connectionError);
      setConnectionError('Connection failed, using fallback mode');
      startPolling(); // Fallback to polling
    }
  };

  useEffect(() => {
    if (jobId) {
      connectToStream();
    }

    return () => {
      // Cleanup on unmount
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [jobId]);

  const disconnect = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      setIsConnected(false);
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
  };

  return {
    status,
    progress,
    result,
    error,
    isConnected,
    connectionError,
    disconnect
  };
};

export default useJobStatus; 