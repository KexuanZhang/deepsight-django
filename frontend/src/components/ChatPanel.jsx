import React, { useState, useEffect, useRef } from "react";
import { Send, Volume2, Copy, ChevronUp, MessageCircle, Loader2, RefreshCw, Settings, User, Bot, Sparkles, FileText, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/components/ui/use-toast";

const ChatPanel = ({ notebookId }) => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { toast } = useToast();

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize with welcome message
  useEffect(() => {
    const welcomeMessage = {
      id: 'welcome',
      type: 'assistant',
      content: 'Hello! I\'m your AI research assistant. I can help you analyze your knowledge base, answer questions about your documents, and provide insights. What would you like to explore today?',
      timestamp: new Date().toISOString(),
      isWelcome: true
    };
    setMessages([welcomeMessage]);
  }, []);

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage("");
    setIsLoading(true);
    setIsTyping(true);
    setError(null);

    try {
      // Simulate AI response (replace with actual API call)
      setTimeout(() => {
        const responses = [
          "I'd be happy to help you analyze that topic. Based on your knowledge base, I can provide detailed insights and connections between your documents.",
          "That's an interesting question! Let me search through your uploaded documents to find relevant information and provide you with a comprehensive answer.",
          "I can see several relevant documents in your knowledge base that relate to this topic. Would you like me to summarize the key findings?",
          "Based on the documents you've uploaded, I can help you understand the connections and draw insights from multiple sources.",
          "Great question! I'm analyzing your knowledge base to provide you with the most accurate and relevant information."
        ];

        const assistantMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: responses[Math.floor(Math.random() * responses.length)],
          timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, assistantMessage]);
        setIsLoading(false);
        setIsTyping(false);
      }, 2000);

    } catch (error) {
      console.error('Chat error:', error);
      setError('Failed to send message. Please try again.');
      setIsLoading(false);
      setIsTyping(false);
      
      toast({
        title: "Message Failed",
        description: "Could not send your message. Please try again.",
        variant: "destructive",
      });
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
      description: "Message copied to clipboard",
    });
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Simple Header */}
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
              onClick={() => setMessages(messages.slice(0, 1))}
            >
              Clear
            </Button>
            {isTyping && (
              <span className="text-xs text-gray-500">typing...</span>
            )}
          </div>
        </div>
      </div>

      {/* Error Display */}
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
      
      {/* Messages Area */}
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
                  message.type === 'user'
                    ? 'bg-gray-900 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}>
                  {message.content}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {/* Typing Indicator */}
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
      
      {/* Empty State */}
      {messages.length <= 1 && !isLoading && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-100 to-blue-200 rounded-2xl mx-auto mb-4 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-blue-500" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Start a conversation</h3>
            <p className="text-sm text-gray-500 mb-6">Ask me anything about your uploaded documents and knowledge base</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                "Summarize my documents",
                "What are the key findings?",
                "Find connections between sources",
                "Explain this topic"
              ].map((suggestion, index) => (
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
      )}
      
      {/* Input Area */}
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
