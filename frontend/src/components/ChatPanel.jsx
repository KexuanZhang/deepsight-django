import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Send, Volume2, Copy, ChevronUp, MessageCircle, Loader2, RefreshCw, Settings, User, Bot, Sparkles, FileText, AlertCircle, HelpCircle
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/components/ui/use-toast";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Memoized markdown content component for assistant messages
const MarkdownContent = React.memo(({ content }) => (
  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-code:text-gray-800 prose-pre:bg-gray-900 prose-pre:text-gray-100">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        h1: ({children}) => <h1 className="text-lg font-bold text-gray-900 mb-3 pb-2 border-b">{children}</h1>,
        h2: ({children}) => <h2 className="text-base font-semibold text-gray-800 mt-4 mb-2">{children}</h2>,
        h3: ({children}) => <h3 className="text-sm font-medium text-gray-800 mt-3 mb-2">{children}</h3>,
        p: ({children}) => <p className="text-gray-700 leading-relaxed mb-2">{children}</p>,
        ul: ({children}) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
        ol: ({children}) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
        li: ({children}) => <li className="text-gray-700 text-sm">{children}</li>,
        blockquote: ({children}) => <blockquote className="border-l-2 border-blue-200 pl-3 italic text-gray-600 my-2">{children}</blockquote>,
        code: ({children}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-xs font-mono text-gray-800">{children}</code>,
        pre: ({children}) => <pre className="bg-gray-900 text-gray-100 p-3 rounded-lg overflow-x-auto my-2 text-xs">{children}</pre>,
        a: ({href, children}) => (
          <a 
            href={href} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            {children}
          </a>
        ),
        table: ({children}) => <table className="min-w-full border-collapse border border-gray-300 my-2">{children}</table>,
        th: ({children}) => <th className="border border-gray-300 px-2 py-1 bg-gray-100 text-xs font-medium">{children}</th>,
        td: ({children}) => <td className="border border-gray-300 px-2 py-1 text-xs">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  </div>
));

MarkdownContent.displayName = 'MarkdownContent';

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

      setMessages(formattedMessages);
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
                  const response = await fetch(`/api/v1/notebooks/${notebookId}/chat-history/clear/`, {
                    method: "DELETE",
                    headers: {
                      "Content-Type": "application/json",
                      "X-CSRFToken": getCookie("csrftoken"),
                    },
                  });

                  if (!response.ok) throw new Error("Failed to clear chat");

                  // Reset to empty messages
                  setMessages([]);

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
                  {message.type === 'user' ? message.content : <MarkdownContent content={message.content} />}
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
      {messages.length === 0 && !isLoading ? (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex-1 flex items-center justify-center p-6"
        >
          <div className="text-center max-w-3xl w-full">
            <motion.div 
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="w-24 h-24 bg-gradient-to-br from-blue-100 via-indigo-100 to-purple-100 rounded-3xl mx-auto mb-8 flex items-center justify-center shadow-lg"
            >
              <MessageCircle className="h-12 w-12 text-blue-600" />
            </motion.div>
            
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="max-w-xl mx-auto"
            >
              <h3 className="text-2xl font-semibold text-gray-900 mb-4">Start a conversation</h3>
              <p className="text-base text-gray-600 mb-10 leading-relaxed">Ask me anything about your uploaded documents and knowledge base. I can help you discover insights, find connections, and explore your content.</p>
            </motion.div>
            
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.3 }}
              className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-4xl mx-auto"
            >
                             {[
                 { text: "Give me an overview of all my documents", icon: FileText },
                 { text: "What are the most important insights and findings?", icon: Sparkles },
                 { text: "How do these sources relate to each other?", icon: RefreshCw },
                 { text: "Help me explore a specific topic in depth", icon: HelpCircle }
               ].map((suggestion, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ 
                    duration: 0.3, 
                    delay: 0.4 + (index * 0.08),
                    ease: "easeOut"
                  }}
                  whileHover={{ scale: 1.02, y: -2 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Button
                    variant="outline"
                    size="lg"
                    className="w-full text-left justify-start bg-white hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 border-gray-200 hover:border-blue-300 text-gray-700 hover:text-blue-700 shadow-sm hover:shadow-md transition-all duration-300 h-auto py-4 px-5 group"
                    onClick={() => handleSendMessage(suggestion.text)}
                  >
                    <div className="flex items-start space-x-4 w-full">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-xl flex items-center justify-center group-hover:from-blue-200 group-hover:to-indigo-200 transition-colors duration-200 flex-shrink-0">
                        <suggestion.icon className="h-5 w-5 text-blue-600" />
                      </div>
                      <div className="flex-1 min-h-[2.5rem] flex items-center">
                        <span className="text-sm leading-relaxed font-medium">{suggestion.text}</span>
                      </div>
                    </div>
                  </Button>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </motion.div>
      ) : suggestedQuestions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3 }}
          className="border-t border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50"
        >
          <div className="px-4 py-4">
            <div className="flex items-center space-x-2 mb-3">
              <div className="w-5 h-5 bg-gradient-to-br from-blue-500 to-indigo-500 rounded-full flex items-center justify-center">
                <Sparkles className="h-3 w-3 text-white" />
              </div>
              <span className="text-sm font-medium text-gray-700">Continue exploring</span>
              <div className="flex-1 h-px bg-gradient-to-r from-gray-300 to-transparent"></div>
            </div>
            
                         <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
               {suggestedQuestions.slice(0, 4).map((question, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ 
                    duration: 0.2, 
                    delay: index * 0.05,
                    ease: "easeOut"
                  }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-left justify-start text-xs bg-white/80 backdrop-blur-sm hover:bg-blue-100 border-gray-200 hover:border-blue-300 text-gray-700 hover:text-blue-700 shadow-sm hover:shadow-md transition-all duration-200 h-auto py-2.5 px-3"
                    onClick={() => handleSendMessage(question)}
                  >
                    <div className="flex items-start space-x-2 w-full">
                      <div className="w-1.5 h-1.5 bg-blue-400 rounded-full mt-1.5 flex-shrink-0"></div>
                      <span className="leading-relaxed line-clamp-2">{question}</span>
                    </div>
                  </Button>
                </motion.div>
              ))}
            </div>
            
                         {suggestedQuestions.length > 4 && (
               <motion.div
                 initial={{ opacity: 0 }}
                 animate={{ opacity: 1 }}
                 transition={{ delay: 0.4 }}
                 className="mt-3 text-center"
               >
                 <Button
                   variant="ghost"
                   size="sm"
                   className="text-xs text-gray-500 hover:text-gray-700"
                   onClick={() => {
                     // Cycle through showing more questions
                     const currentShown = 4;
                     const totalQuestions = suggestedQuestions.length;
                     // Could implement a show more functionality here
                   }}
                 >
                   <ChevronUp className="h-3 w-3 mr-1" />
                   {suggestedQuestions.length - 4} more suggestions
                 </Button>
               </motion.div>
             )}
          </div>
        </motion.div>
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