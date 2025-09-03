import { useState, useEffect, useRef, useCallback } from 'react';
import { useToast } from "@/shared/components/ui/use-toast";
import chatService from "@/features/notebook/services/ChatService";
import type { NotebookChatMessage } from "@/features/notebook/type";

// File interface
interface FileReference {
  file_id?: string;
  file?: string;
  metadata?: {
    knowledge_item_id?: string;
    [key: string]: any;
  };
  [key: string]: any;
}

// Sources list ref interface
interface SourcesListRef {
  current: {
    getSelectedFiles: () => FileReference[];
  } | null;
}

// Hook return type
interface UseChatReturn {
  messages: NotebookChatMessage[];
  inputMessage: string;
  setInputMessage: (message: string) => void;
  isLoading: boolean;
  error: string | null;
  setError: (error: string | null) => void;
  isTyping: boolean;
  suggestedQuestions: string[];
  messagesEndRef: React.RefObject<HTMLDivElement>;
  sendMessage: (overrideMessage?: string | null) => Promise<{ success: boolean; message?: NotebookChatMessage; error?: string }>;
  clearChatHistory: () => Promise<{ success: boolean; error?: string }>;
  copyMessage: (content: string) => void;
  handleKeyPress: (e: React.KeyboardEvent) => void;
  fetchSuggestions: () => Promise<string[]>;
  fetchChatHistory: () => Promise<{ success: boolean; messages?: NotebookChatMessage[]; error?: string }>;
}

/**
 * Custom hook for chat functionality
 * Handles chat messages, suggestions, caching, and real-time communication
 */
export const useChat = (notebookId: string, sourcesListRef: SourcesListRef): UseChatReturn => {
  const [messages, setMessages] = useState<NotebookChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Helper to get CSRF token
  const getCookie = useCallback((name: string): string | null => {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match && match[2] ? decodeURIComponent(match[2]) : null;
  }, []);

  // Scroll to bottom of messages
  const scrollToBottom = useCallback((): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Cache management for suggestions
  const getCachedSuggestions = useCallback((): string[] => {
    try {
      const cached = localStorage.getItem(`suggestedQuestions_${notebookId}`);
      return cached ? JSON.parse(cached) : [];
    } catch (error) {
      console.error('Error loading cached suggestions:', error);
      return [];
    }
  }, [notebookId]);

  const cacheSuggestions = useCallback((suggestions: string[]): void => {
    try {
      localStorage.setItem(`suggestedQuestions_${notebookId}`, JSON.stringify(suggestions));
    } catch (error) {
      console.error('Error caching suggestions:', error);
    }
  }, [notebookId]);

  // Fetch chat history
  const fetchChatHistory = useCallback(async () => {
    try {
      const messages = await chatService.getChatHistory(notebookId);
      setMessages(messages);
      
      // Load cached suggestions if there are messages
      if (messages.length > 0) {
        const cachedSuggestions = getCachedSuggestions();
        if (cachedSuggestions.length > 0) {
          setSuggestedQuestions(cachedSuggestions);
        }
      }
      
      return { success: true, messages };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error("Could not load chat history:", err);
      toast({
        title: "Failed to load chat history",
        description: "We could not fetch the previous conversation.",
        variant: "destructive"
      });
      return { success: false, error: errorMessage };
    }
  }, [notebookId, getCachedSuggestions, toast]);

  // Fetch suggested questions
  const fetchSuggestions = useCallback(async () => {
    try {
      const suggestions = await chatService.getSuggestedQuestions(notebookId);
      setSuggestedQuestions(suggestions);
      return suggestions;
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
  const sendMessage = useCallback(async (overrideMessage?: string | null) => {
    const messageToSend = overrideMessage || inputMessage.trim();
    if (!messageToSend || isLoading) return { success: false, error: 'No message to send or already loading' };

    const userMessage: NotebookChatMessage = {
      id: Date.now().toString(),
      role: 'user',
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
    const selectedFileIds = currentSelectedFiles.map(file => 
      // Use knowledge_item_id from metadata, fallback to file_id or file for backward compatibility
      file.metadata?.knowledge_item_id || file.file_id || file.file
    ).filter((id): id is string => Boolean(id));

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
      return { success: false, error: "No documents selected" };
    }

    try {
      const response = await chatService.sendChatMessage(notebookId, selectedFileIds, userMessage.content);

      const assistantMessage: NotebookChatMessage = {
        id: response.message.id,
        role: 'assistant',
        content: response.message.content,
        timestamp: response.message.timestamp
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Cache new suggestions if provided
      if (response.suggested_questions && response.suggested_questions.length > 0) {
        setSuggestedQuestions(response.suggested_questions);
        cacheSuggestions(response.suggested_questions);
      }
      
      return { success: true, message: assistantMessage };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error("Chat error:", err);
      setError("Failed to get a response from the AI. Please try again.");
      toast({
        title: "Message Failed",
        description: "Could not connect to the backend. Please try again.",
        variant: "destructive"
      });
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  }, [inputMessage, isLoading, getCurrentSelectedFiles, notebookId, toast, cacheSuggestions]);

  // Clear chat history
  const clearChatHistory = useCallback(async () => {
    try {
      await chatService.clearChatHistory(notebookId);

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
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error("Error clearing chat:", err);
      toast({
        title: "Error",
        description: "Could not clear chat history.",
        variant: "destructive",
      });
      return { success: false, error: errorMessage };
    }
  }, [notebookId, toast]);

  // Copy message to clipboard
  const copyMessage = useCallback((content: string) => {
    navigator.clipboard.writeText(content);
    toast({
      title: "Copied",
      description: "Message copied to clipboard"
    });
  }, [toast]);

  // Handle keyboard input
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
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