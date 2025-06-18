import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (jobId, onComplete, onError) => {
  const [status, setStatus] = useState(null);
  const [progress, setProgress] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState(null);
  
  const websocketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5; // Reduced from 10 to prevent excessive reconnections
  const pingIntervalRef = useRef(null);
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

  // Function to send a message via WebSocket
  const sendMessage = useCallback((message) => {
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      try {
        websocketRef.current.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Error sending WebSocket message:', error);
        return false;
      }
    }
    return false;
  }, []);

  // Function to send cancellation request
  const cancelJob = useCallback(() => {
    if (!currentJobIdRef.current) {
      console.warn('No job ID available for cancellation');
      return false;
    }
    
    return sendMessage({
      type: 'cancel_job'
    });
  }, [sendMessage]);

  // Function to send ping for keep-alive
  const sendPing = useCallback(() => {
    return sendMessage({
      type: 'ping'
    });
  }, [sendMessage]);

  // Start ping interval for connection keep-alive
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }
    
    pingIntervalRef.current = setInterval(() => {
      if (!sendPing()) {
        console.warn('Failed to send ping, connection may be broken');
      }
    }, 30000); // Ping every 30 seconds
  }, [sendPing]);

  // Stop ping interval
  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Clean up connection
  const cleanupConnection = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    stopPingInterval();
    if (websocketRef.current) {
      websocketRef.current.close(1000, 'Cleanup');
      websocketRef.current = null;
    }
    isConnectingRef.current = false;
    setIsConnected(false);
  }, [stopPingInterval]);

  // WebSocket connection function - now stable with useCallback and no external dependencies
  const connectWebSocket = useCallback(() => {
    const currentJobId = currentJobIdRef.current;
    
    console.log('connectWebSocket called for job:', currentJobId);
    
    if (!currentJobId) {
      console.warn('No job ID provided for WebSocket connection');
      return;
    }

    // Prevent multiple simultaneous connection attempts
    if (isConnectingRef.current) {
      console.warn('WebSocket connection already in progress for job:', currentJobId);
      return;
    }

    // Check if we already have a connection for this job
    if (websocketRef.current && 
        websocketRef.current.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected for job:', currentJobId);
      return;
    }

    console.log('Starting new WebSocket connection for job:', currentJobId);
    isConnectingRef.current = true;

    // Clean up existing connection
    if (websocketRef.current && websocketRef.current.readyState !== WebSocket.CLOSED) {
      console.log('Closing existing WebSocket connection');
      websocketRef.current.close();
    }

    try {
      // Use the backend WebSocket endpoint
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname + ':8000'; // Backend port
      const wsUrl = `${protocol}//${host}/api/v1/ws/job-status/${currentJobId}`;
      
      console.log('Connecting to WebSocket:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      websocketRef.current = ws;

      // Add connection timeout
      const connectionTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          console.error('WebSocket connection timeout for job:', currentJobId);
          ws.close();
          isConnectingRef.current = false;
          setConnectionError('Connection timeout. Please try refreshing the page.');
        }
      }, 10000); // 10 second timeout

      ws.onopen = () => {
        clearTimeout(connectionTimeout);
        console.log('WebSocket connected for job:', currentJobId);
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        isConnectingRef.current = false;
        startPingInterval();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data);
          
          switch (data.type) {
            case 'status_update':
              setStatus(data.status);
              setProgress(data.progress || '');
              
              if (data.result) {
                setResult(data.result);
              }
              if (data.error) {
                setError(data.error);
              }
              
              // Check if job is complete
              if (data.status === 'completed' && onCompleteRef.current) {
                onCompleteRef.current(data.result);
              } else if (data.status === 'failed' && onErrorRef.current) {
                onErrorRef.current(data.error || 'Job failed');
              } else if (data.status === 'cancelled') {
                setProgress('Job was cancelled');
              }
              break;
              
            case 'job_finished':
              console.log('Job finished:', data);
              setStatus(data.status);
              
              if (data.status === 'completed' && onCompleteRef.current) {
                onCompleteRef.current(data.result);
              } else if (data.status === 'failed' && onErrorRef.current) {
                onErrorRef.current(data.error || 'Job failed');
              }
              
              // Close connection as job is finished
              setTimeout(() => {
                cleanupConnection();
              }, 1000);
              break;
              
            case 'cancel_response':
              if (data.success) {
                console.log('Job cancellation confirmed:', data.job_id);
                setStatus('cancelled');
                setProgress('Job cancelled by user');
              } else {
                console.error('Job cancellation failed');
                setError('Failed to cancel job');
              }
              break;
              
            case 'pong':
              // Keep-alive response, connection is healthy
              break;
              
            case 'heartbeat':
              // Server heartbeat, connection is healthy
              break;
              
            case 'error':
              console.error('WebSocket error message:', data.message);
              setError(data.message);
              if (onErrorRef.current) {
                onErrorRef.current(data.message);
              }
              break;
              
            default:
              console.warn('Unknown WebSocket message type:', data.type);
          }
        } catch (parseError) {
          console.error('Error parsing WebSocket message:', parseError, 'Raw message:', event.data);
        }
      };

      ws.onclose = (event) => {
        clearTimeout(connectionTimeout);
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        isConnectingRef.current = false;
        stopPingInterval();
        
        // Only attempt reconnection if it wasn't a normal closure, we haven't exceeded max attempts,
        // and we still have the same job ID
        if (event.code !== 1000 && 
            event.code !== 1001 && 
            reconnectAttemptsRef.current < maxReconnectAttempts &&
            currentJobIdRef.current === currentJobId) {
          
          const delay = Math.min(Math.pow(2, reconnectAttemptsRef.current) * 1000, 15000); // Max 15 seconds
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          setConnectionError(`Connection lost, reconnecting in ${Math.ceil(delay/1000)}s...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connectWebSocket();
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error('Max reconnection attempts reached');
          setConnectionError('Connection failed. Please refresh the page.');
        }
      };

      ws.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error('WebSocket error:', error);
        setConnectionError('WebSocket connection error');
        isConnectingRef.current = false;
      };

    } catch (error) {
      console.error('Error creating WebSocket:', error);
      setConnectionError('Failed to create WebSocket connection');
      isConnectingRef.current = false;
    }
  }, [startPingInterval, stopPingInterval, cleanupConnection]);

  // Connect when jobId changes - simplified effect
  useEffect(() => {
    console.log('useWebSocket effect triggered, jobId:', jobId);
    
    if (jobId) {
      // Reset connection state for new job
      reconnectAttemptsRef.current = 0;
      setStatus(null);
      setProgress('');
      setResult(null);
      setError(null);
      setConnectionError(null);
      
      console.log('Starting WebSocket connection for job:', jobId);
      connectWebSocket();
    } else {
      // Clean up if no job ID
      console.log('No jobId, cleaning up WebSocket connection');
      cleanupConnection();
    }

    // Cleanup function
    return () => {
      console.log('useWebSocket cleanup for job:', jobId);
      cleanupConnection();
    };
  }, [jobId, connectWebSocket, cleanupConnection]);

  return {
    status,
    progress,
    result,
    error,
    isConnected,
    connectionError,
    cancelJob,
    sendMessage,
    reconnect: connectWebSocket
  };
}; 