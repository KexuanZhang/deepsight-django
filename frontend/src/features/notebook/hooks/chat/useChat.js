import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from '@/common/components/ui/use-toast';
import { config } from '@/config';

/**
 * Custom hook for chat functionality
 * Handles chat messages, suggestions, caching, and real-time communication
 */
export const useChat = (notebookId, sourcesListRef) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const messagesEndRef = useRef(null);
  const { toast } = useToast();

  // Helper to get CSRF token
  const getCookie = useCallback((name) => {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match ? decodeURIComponent(match[2]) : null;
  }, []);

  // Scroll to bottom of messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Cache management for suggestions
  const getCachedSuggestions = useCallback(() => {
    try {
      const cached = localStorage.getItem(`suggestedQuestions_${notebookId}`);
      return cached ? JSON.parse(cached) : [];
    } catch (error) {
      console.error('Error loading cached suggestions:', error);
      return [];
    }
  }, [notebookId]);

  const cacheSuggestions = useCallback((suggestions) => {
    try {
      localStorage.setItem(`suggestedQuestions_${notebookId}`, JSON.stringify(suggestions));
    } catch (error) {
      console.error('Error caching suggestions:', error);
    }
  }, [notebookId]);

  // Fetch chat history
  const fetchChatHistory = useCallback(async () => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/chat-history/`, {
        credentials: 'include',
      });
      
      if (!response.ok) throw new Error("Failed to fetch chat history");
      
      const data = await response.json();
      const formattedMessages = data.history.map((msg) => ({
        id: msg.id.toString(),
        type: msg.sender === "user" ? "user" : "assistant",
        content: msg.message,
        timestamp: msg.timestamp,
        isWelcome: false
      }));

      setMessages(formattedMessages);
      
      // Load cached suggestions if there are messages
      if (formattedMessages.length > 0) {
        const cachedSuggestions = getCachedSuggestions();
        if (cachedSuggestions.length > 0) {
          setSuggestedQuestions(cachedSuggestions);
        }
      }
      
      return { success: true, messages: formattedMessages };
    } catch (err) {
      console.error("Could not load chat history:", err);
      toast({
        title: "Failed to load chat history",
        description: "We could not fetch the previous conversation.",
        variant: "destructive"
      });
      return { success: false, error: err.message };
    }
  }, [notebookId, getCachedSuggestions, toast]);

  // Fetch suggested questions
  const fetchSuggestions = useCallback(async () => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/suggested-questions/`, {
        credentials: 'include',
      });
      if (!response.ok) throw new Error("Failed to fetch suggestions");
      const data = await response.json();
      setSuggestedQuestions(data.suggestions || []);
      return data.suggestions || [];
    } catch (err) {
      console.error("Failed to load suggestions:", err);
      return [];
    }
  }, [notebookId]);

  // Get selected files from sources
  const getCurrentSelectedFiles = useCallback(() => {
    if (!sourcesListRef?.current?.getSelectedFiles) {
      return [];
    }
    return sourcesListRef.current.getSelectedFiles();
  }, [sourcesListRef]);

  // Send message
  const sendMessage = useCallback(async (overrideMessage = null) => {
    const messageToSend = overrideMessage || inputMessage.trim();
    if (!messageToSend || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: messageToSend.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setIsTyping(true);
    setError(null);
    setSuggestedQuestions([]);

    // Get selected files
    const currentSelectedFiles = getCurrentSelectedFiles();
    const selectedFileIds = currentSelectedFiles.map(file => file.file_id || file.file).filter(id => id);

    // Validate file selection
    if (selectedFileIds.length === 0) {
      setIsLoading(false);
      setIsTyping(false);
      setError("Please select at least one document from your sources to start a conversation.");
      toast({
        title: "No Documents Selected",
        description: "Please select at least one document from the sources panel to chat about your knowledge base.",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/chat/`, {
        method: "POST",
        credentials: 'include',
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({
          file_ids: selectedFileIds,
          question: userMessage.content,
          notebook_id: notebookId
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: data.answer,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Fetch follow-up suggestions
      const followupResp = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/suggested-questions/`, {
        credentials: 'include',
      });
      const followupData = await followupResp.json();
      const newSuggestions = followupData.suggestions || [];
      setSuggestedQuestions(newSuggestions);
      
      // Cache suggestions
      if (newSuggestions.length > 0) {
        cacheSuggestions(newSuggestions);
      }
      
      return { success: true, message: assistantMessage };
    } catch (err) {
      console.error("Chat error:", err);
      setError("Failed to get a response from the AI. Please try again.");
      toast({
        title: "Message Failed",
        description: "Could not connect to the backend. Please try again.",
        variant: "destructive"
      });
      return { success: false, error: err.message };
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  }, [inputMessage, isLoading, getCurrentSelectedFiles, notebookId, getCookie, toast, cacheSuggestions]);

  // Clear chat history
  const clearChatHistory = useCallback(async () => {
    try {
      const response = await fetch(`${config.API_BASE_URL}/notebooks/${notebookId}/chat-history/clear/`, {
        method: "DELETE",
        credentials: 'include',
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
      });

      if (!response.ok) throw new Error("Failed to clear chat");

      setMessages([]);
      setSuggestedQuestions([]);
      
      // Clear cached suggestions
      try {
        localStorage.removeItem(`suggestedQuestions_${notebookId}`);
      } catch (error) {
        console.error('Error clearing cached suggestions:', error);
      }

      toast({
        title: "Chat Cleared",
        description: "Previous chat history was successfully removed.",
      });
      
      return { success: true };
    } catch (err) {
      console.error("Error clearing chat:", err);
      toast({
        title: "Error",
        description: "Could not clear chat history.",
        variant: "destructive",
      });
      return { success: false, error: err.message };
    }
  }, [notebookId, getCookie, toast]);

  // Copy message to clipboard
  const copyMessage = useCallback((content) => {
    navigator.clipboard.writeText(content);
    toast({
      title: "Copied",
      description: "Message copied to clipboard"
    });
  }, [toast]);

  // Handle keyboard input
  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  // Auto-scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load chat history on mount
  useEffect(() => {
    if (notebookId) {
      fetchChatHistory();
    }
  }, [notebookId, fetchChatHistory]);

  return {
    messages,
    inputMessage,
    setInputMessage,
    isLoading,
    error,
    setError,
    isTyping,
    suggestedQuestions,
    messagesEndRef,
    sendMessage,
    clearChatHistory,
    copyMessage,
    handleKeyPress,
    fetchSuggestions,
    fetchChatHistory,
  };
};