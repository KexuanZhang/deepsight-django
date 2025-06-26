import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Send, Volume2, Copy, ChevronUp, MessageCircle, Loader2, RefreshCw, Settings, User, Bot, Sparkles, FileText, AlertCircle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/components/ui/use-toast";

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

const ChatPanel = ({ notebookId, sourcesListRef, onSelectionChange }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { toast } = useToast();
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [selectedSources, setSelectedSources] = useState([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);

  const updateSelectedFiles = useCallback(() => {
    if (sourcesListRef?.current) {
      // console.log("changing")
      const newSelectedFiles = sourcesListRef.current.getSelectedFiles() || [];
      const newSelectedSources = sourcesListRef.current.getSelectedSources() || [];
      // console.log("change", newSelectedFiles)
      setSelectedFiles(newSelectedFiles);
      setSelectedSources(newSelectedSources);
      // console.log("after", selectedFiles)
    }
  }, [sourcesListRef]);

  // useEffect(() => {
  //   const fetchSuggestions = async () => {
  //     try {
  //       const response = await fetch(`/api/v1/notebooks/${notebookId}/suggested-questions/`);
  //       if (!response.ok) throw new Error("Failed to fetch suggestions");
  //       const data = await response.json();
  //       setSuggestedQuestions(data.suggestions || []);
  //     } catch (err) {
  //       console.error("Failed to load suggestions:", err);
  //     }
  //   };

  //   if (notebookId) fetchSuggestions();
  // }, [notebookId]);
    const fetchSuggestions = async () => {
    try {
      const response = await fetch(`/api/v1/notebooks/${notebookId}/suggested-questions/`);
      if (!response.ok) throw new Error("Failed to fetch suggestions");
      const data = await response.json();
      setSuggestedQuestions(data.suggestions || []);
    } catch (err) {
      console.error("Failed to load suggestions:", err);
    }
  };

  useEffect(() => {
    console.log("Updated state - selectedFiles:", selectedFiles);
  }, [selectedFiles]);

  useEffect(() => {
    console.log("Updated state - selectedSources:", selectedSources);
  }, [selectedSources]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

    // Register callback with parent component only once
  useEffect(() => {
    if (onSelectionChange) {
      console.log("use effect")
      onSelectionChange(updateSelectedFiles);
    }
  }, [onSelectionChange, updateSelectedFiles]);
    
    // Initial load with a small delay to avoid race conditions
  useEffect(() => {
    const timer = setTimeout(() => {
      updateSelectedFiles();
    }, 200);
      
    return () => clearTimeout(timer);
  }, []); // Empty dependency array for one-time initial load
    

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

useEffect(() => {
  const fetchChatHistory = async () => {
    try {
      const response = await fetch(`/api/v1/notebooks/${notebookId}/chat-history/`);
      if (!response.ok) throw new Error("Failed to fetch chat history");
      const data = await response.json();
      const formattedMessages = data.history.map((msg) => ({
        id: msg.id.toString(),
        type: msg.sender === "user" ? "user" : "assistant",
        content: msg.message,
        timestamp: msg.timestamp,
        isWelcome: false
      }));

      if (data.history && data.history.length > 0) {
        setMessages(formattedMessages);
      } else {
        setMessages([
          {
            id: 'welcome',
            type: 'assistant',
            content: 'Hello! I\'m your AI research assistant. I can help you analyze your knowledge base, answer questions about your documents, and provide insights. What would you like to explore today?',
            timestamp: new Date().toISOString(),
            isWelcome: true
          }
        ]);
      }
    } catch (err) {
      console.error("Could not load chat history:", err);
      toast({
        title: "Failed to load chat history",
        description: "We could not fetch the previous conversation.",
        variant: "destructive"
      });
    }
  };

  if (notebookId) fetchChatHistory();
}, [notebookId]);


  const handleSendMessage = async (overrideMessage = null) => {
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

    // Get the LATEST selected files directly from SourcesList ref to ensure we have current data
    const currentSelectedFiles = sourcesListRef?.current?.getSelectedFiles() || [];

    // Debug: Log selected files structure
    console.log("=== CHAT DEBUG ===");
    console.log("State selectedFiles:", selectedFiles.length);
    console.log("Current selectedFiles from ref:", currentSelectedFiles.length);
    console.log("currentSelectedFiles structure:", currentSelectedFiles);
    
    // Use current files directly from the ref to ensure we have the latest selection
    const readyFiles = currentSelectedFiles;
    
    // Log each file for debugging
    readyFiles.forEach(file => {
      console.log(`Ready file "${file.title || file.name}":`, {
        file_id: file.file_id,
        file: file.file,
        parsing_status: file.parsing_status,
        hasValidId: !!(file.file_id || file.file)
      });
    });
    
    // Extract file_id which is the knowledge base item ID
    // Handle both file_id and file properties (as per SourcesList logic)
    const selectedFileIds = readyFiles.map(file => file.file_id || file.file).filter(id => id);
    
    console.log("Filtered readyFiles:", readyFiles);
    console.log("Final selectedFileIds (knowledge base item IDs):", selectedFileIds);
    console.log("=== END CHAT DEBUG ===");

    try {
      const response = await fetch("/api/v1/notebooks/chat/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),  // if you're using CSRF protection
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
      
      const followupResp = await fetch(`/api/v1/notebooks/${notebookId}/suggested-questions/`);
      const followupData = await followupResp.json();
      setSuggestedQuestions(followupData.suggestions || []);
    } catch (err) {
      console.error("Chat error:", err);
      setError("Failed to get a response from the AI. Please try again.");
      toast({
        title: "Message Failed",
        description: "Could not connect to the backend. Please try again.",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleCopyMessage = (content) => {
    navigator.clipboard.writeText(content);
    toast({
      title: "Copied",
      description: "Message copied to clipboard"
    });
  };

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-6 h-6 bg-gray-100 rounded-md flex items-center justify-center">
              <MessageCircle className="h-3 w-3 text-gray-600" />
            </div>
            <h3 className="text-sm font-medium text-gray-900">Chat</h3>
          </div>
          <div className="flex items-center space-x-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-gray-500 hover:text-gray-700"
              onClick={async () => {
                try {
                  const response = await fetch(`/api/v1/notebooks/${notebookId}/chat/clear/`, {
                    method: "DELETE",
                    headers: {
                      "Content-Type": "application/json",
                      "X-CSRFToken": getCookie("csrftoken"),
                    },
                  });

                  if (!response.ok) throw new Error("Failed to clear chat");

                  // Reset with welcome message
                  setMessages([
                    {
                      id: "welcome",
                      type: "assistant",
                      content:
                        "Hello! I’m your AI research assistant. I can help you analyze your knowledge base, answer questions about your documents, and provide insights. What would you like to explore today?",
                      timestamp: new Date().toISOString(),
                      isWelcome: true,
                    },
                  ]);

                  toast({
                    title: "Chat Cleared",
                    description: "Previous chat history was successfully removed.",
                  });
                } catch (err) {
                  console.error("Error clearing chat:", err);
                  toast({
                    title: "Error",
                    description: "Could not clear chat history.",
                    variant: "destructive",
                  });
                }
              }}
            >
              Clear
            </Button>

            {isTyping && <span className="text-xs text-gray-500">typing...</span>}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-shrink-0 p-4 border-b border-gray-200"
          >
            <Alert variant="destructive" className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm text-red-800">
                {error}
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-2 h-6 px-2 text-red-600 hover:text-red-800"
                  onClick={() => setError(null)}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex space-x-2 max-w-[80%] ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                  {message.type === 'user' ? (
                    <User className="h-3 w-3 text-gray-600" />
                  ) : (
                    <Bot className="h-3 w-3 text-gray-600" />
                  )}
                </div>
                <div className={`px-3 py-2 rounded-lg text-sm ${
                  message.type === 'user' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-900'
                }`}>
                  {message.content}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="flex space-x-2">
              <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center">
                <Bot className="h-3 w-3 text-gray-600" />
              </div>
              <div className="bg-gray-100 rounded-lg px-3 py-2 flex items-center space-x-1">
                <Loader2 className="h-3 w-3 animate-spin text-gray-500" />
                <span className="text-xs text-gray-500">typing...</span>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* {messages.length <= 1 && !isLoading && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start a conversation</h3>
            <p className="text-sm text-gray-500 mb-6">Ask me anything about your uploaded documents and knowledge base</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {["Summarize my documents", "What are the key findings?", "Find connections between sources", "Explain this topic"].map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="text-xs bg-white hover:bg-blue-50 border-gray-300 hover:border-blue-300 text-gray-700 hover:text-blue-700"
                  onClick={() => setInputMessage(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        </div>
      )} */}
      {messages.length <= 1 && !isLoading ? (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start a conversation</h3>
            <p className="text-sm text-gray-500 mb-6">Ask me anything about your uploaded documents and knowledge base</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {["Summarize my documents", "What are the key findings?", "Find connections between sources", "Explain this topic"].map((suggestion, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="text-xs bg-white hover:bg-blue-50 border-gray-300 hover:border-blue-300 text-gray-700 hover:text-blue-700"
                  onClick={() => handleSendMessage(suggestion)}
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        </div>
      ) : suggestedQuestions.length > 0 && (
        <div className="px-4 py-2 border-t border-gray-200 bg-gray-50">
          <div className="text-xs font-medium text-gray-500 mb-2">Suggested Questions</div>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((question, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                className="text-xs bg-white hover:bg-blue-50 border-gray-300 text-gray-700"
                onClick={() => handleSendMessage(question)}
              >
                {question}
              </Button>
            ))}
          </div>
        </div>
      )}


      <div className="flex-shrink-0 p-4 border-t border-gray-200">
        <div className="flex space-x-2">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask about your knowledge base..."
            className="flex-1 min-h-[36px] max-h-32 px-3 py-2 border border-gray-300 rounded-md resize-none text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 focus:border-transparent"
            disabled={isLoading}
          />
          <Button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            size="sm"
            className="px-3 py-2 bg-gray-900 hover:bg-gray-800 text-white"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
