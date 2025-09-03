import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import { config } from "@/config";

class AbortError extends Error {
  constructor() {
    super('AbortError');
    this.name = 'AbortError';
  }
}

interface FileStatusData {
  file_id: string;
  status: string;
  title: string;
  updated_at: string | null;
}

export const useFileStatus = (
  fileId: string | null,
  notebookId: string,
  onComplete: (result: FileStatusData) => void,
  onError: (error: string) => void
) => {
  // Validate required parameters
  if (fileId && !notebookId) {
    throw new Error('notebookId is required when fileId is provided');
  }
  
  const [status, setStatus] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  
  const ctrlRef = useRef<AbortController | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const isConnectingRef = useRef(false);
  const processingCompletedRef = useRef(false);
  
  // Store callbacks in refs to avoid recreating connections when they change
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);
  const currentFileIdRef = useRef(fileId);
  const currentNotebookIdRef = useRef(notebookId);

  // Update refs when props change
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    currentFileIdRef.current = fileId;
    currentNotebookIdRef.current = notebookId;
    // Reset completion flag when file ID changes
    if (fileId !== currentFileIdRef.current) {
      processingCompletedRef.current = false;
    }
  }, [fileId, notebookId]);

  const connectEventSource = useCallback(() => {
    if (!currentFileIdRef.current || processingCompletedRef.current || isConnectingRef.current) {
      console.log('Skipping file SSE connection:', { 
        hasFileId: !!currentFileIdRef.current, 
        isCompleted: processingCompletedRef.current, 
        isConnecting: isConnectingRef.current 
      });
      return;
    }

    isConnectingRef.current = true;
    console.log('Starting file SSE connection for file:', currentFileIdRef.current);
    
    // Create a new AbortController for this connection attempt
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    
    try {
      // Determine if this is an upload file (string) or processed file (UUID)
      const fileId = currentFileIdRef.current;
      const isUUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(fileId);
      
      // Build SSE URL based on file type
      const sseUrl = isUUID 
        ? `${config.API_BASE_URL}/notebooks/${currentNotebookIdRef.current}/files/${fileId}/status/stream/`
        : `${config.API_BASE_URL}/notebooks/${currentNotebookIdRef.current}/files/${fileId}/status/stream`;
      
      console.log('Connecting to file SSE:', sseUrl, 'isUUID:', isUUID);
      
      fetchEventSource(sseUrl, {
        method: 'GET',
        headers: {
          'Accept': 'text/event-stream',
        },
        credentials: 'include', // Use session-based authentication
        signal: ctrl.signal,

        onopen: async (response) => {
          if (response.ok && response.headers.get('content-type')?.includes('text/event-stream')) {
            console.log('File SSE Connection opened successfully');
            setIsConnected(true);
            setConnectionError(null);
            reconnectAttemptsRef.current = 0;
            isConnectingRef.current = false;
          } else if (response.status >= 400 && response.status < 500 && response.status !== 429) {
            console.error('Client-side error opening file SSE connection:', response.status, response.statusText);
            setConnectionError('Client-side error connecting to server.');
            throw new AbortError(); // Don't retry on client errors
          } else {
            console.error('Server-side error opening file SSE connection:', response.status, response.statusText);
            setConnectionError('Server-side error connecting.');
            // Let the default retry mechanism handle server errors
          }
        },

        onmessage: (event) => {
          try {
            const parsedEvent = JSON.parse(event.data);
            console.log('Received file SSE data:', parsedEvent);

            // Check for control messages
            if (parsedEvent.type === 'close') {
              console.log('File stream closed by server.');
              processingCompletedRef.current = true;
              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
              return;
            }
            
            if (parsedEvent.type === 'file_status' && parsedEvent.data) {
              const fileData = parsedEvent.data;

              setStatus(fileData.status);
              
              console.log('File status update:', fileData.status, 'for file:', fileData.file_id);
              
              if (fileData.status === 'done') {
                processingCompletedRef.current = true;
                
                if (onCompleteRef.current) {
                  onCompleteRef.current(fileData);
                }
                
                if (ctrlRef.current) ctrlRef.current.abort();
                setIsConnected(false);
                
              } else if (fileData.status === 'error') {
                processingCompletedRef.current = true;
                const errorMsg = 'File processing failed';
                
                if (onErrorRef.current) {
                  onErrorRef.current(errorMsg);
                }
                
                if (ctrlRef.current) ctrlRef.current.abort();
                setIsConnected(false);
              }
            } else if (parsedEvent.type === 'error') {
              console.error('Server error in file SSE:', parsedEvent.message);
              const errorMsg = parsedEvent.message || 'File processing error';
              
              if (onErrorRef.current) {
                onErrorRef.current(errorMsg);
              }
              
              if (ctrlRef.current) ctrlRef.current.abort();
              setIsConnected(false);
            }
          } catch (error) {
            console.error('Error parsing file SSE data:', error);
          }
        },

        onerror: (err) => {
          console.error('File SSE Connection error:', err);
          setIsConnected(false);
          isConnectingRef.current = false;
          
          if (err.name === 'AbortError') {
            console.log('File SSE connection aborted intentionally.');
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
          console.log('File SSE connection closed.');
          setIsConnected(false);
          isConnectingRef.current = false;
        }
      });

    } catch (error) {
      console.error('Failed to create file EventSource:', error);
      setConnectionError('Failed to connect to server');
      isConnectingRef.current = false;
    }

  }, []);

  // Function to disconnect from current file monitoring
  const disconnect = useCallback(() => {
    if (import.meta.env.DEV) {
      console.log('Disconnecting from file status updates');
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
    setConnectionError(null);
    reconnectAttemptsRef.current = 0;
    isConnectingRef.current = false;
    processingCompletedRef.current = false;
  }, []);

  // Effect to handle file ID changes
  useEffect(() => {
    if (fileId && notebookId) {
      // Reset state for new file
      disconnect(); // Ensure any previous connection is closed
      
      // Start SSE connection
      connectEventSource();
    } else {
      // Disconnect when no file ID
      disconnect();
    }
    
    return () => {
      disconnect(); // Cleanup on unmount
    };
  }, [fileId, notebookId, connectEventSource, disconnect]);

  return { status, isConnected, connectionError, disconnect };
};