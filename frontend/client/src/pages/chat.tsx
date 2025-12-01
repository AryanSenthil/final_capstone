import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  Bot,
  User,
  Database,
  Brain,
  PlayCircle,
  FileBarChart,
  Loader2,
  Plus,
  X,
  MessageSquare,
  Settings2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Wrench,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Types
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

interface ToolCall {
  name: string;
  arguments: Record<string, any>;
  result?: any;
}

// API functions
const API_BASE = "/api/chat";

async function fetchSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

async function fetchSessionMessages(sessionId: string): Promise<{ messages: ChatMessage[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

async function deleteSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

// Streaming chat function
async function* streamChat(
  message: string,
  sessionId?: string
): AsyncGenerator<{ type: string; data: any }> {
  const res = await fetch(`${API_BASE}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) throw new Error("Failed to send message");

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: data.type, data };
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}

// Markdown components for styling - Claude/ChatGPT style
const markdownComponents = {
  p: ({ children }: any) => (
    <p className="mb-4 last:mb-0 text-slate-800 dark:text-slate-200 leading-7 text-[15px]">{children}</p>
  ),
  strong: ({ children }: any) => (
    <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
  ),
  em: ({ children }: any) => <em className="italic">{children}</em>,
  ul: ({ children }: any) => (
    <ul className="mb-4 last:mb-0 pl-6 space-y-2 list-disc marker:text-slate-400 dark:marker:text-slate-500">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="mb-4 last:mb-0 pl-6 space-y-2 list-decimal marker:text-slate-500 dark:marker:text-slate-400">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="text-slate-800 dark:text-slate-200 leading-7 pl-1 text-[15px]">{children}</li>
  ),
  code: ({ children, className }: any) => {
    // Check if it's inline code (no className) or code block
    const isInline = !className;
    if (isInline) {
      return (
        <code className="bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-1.5 py-0.5 rounded text-sm font-mono border border-slate-200 dark:border-slate-700">
          {children}
        </code>
      );
    }
    return <code className={className}>{children}</code>;
  },
  pre: ({ children }: any) => (
    <pre className="bg-slate-900 dark:bg-slate-950 text-slate-100 p-4 rounded-lg overflow-x-auto my-4 text-sm font-mono leading-6 border border-slate-700">
      {children}
    </pre>
  ),
  h1: ({ children }: any) => (
    <h1 className="text-xl font-semibold mb-4 mt-6 first:mt-0 text-slate-900 dark:text-white">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-lg font-semibold mb-3 mt-5 first:mt-0 text-slate-900 dark:text-white">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-base font-semibold mb-2 mt-4 first:mt-0 text-slate-900 dark:text-white">{children}</h3>
  ),
  h4: ({ children }: any) => (
    <h4 className="text-[15px] font-semibold mb-2 mt-3 first:mt-0 text-slate-900 dark:text-white">{children}</h4>
  ),
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-4 border-slate-300 dark:border-slate-600 pl-4 my-4 text-slate-600 dark:text-slate-400 italic text-[15px]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-6 border-slate-200 dark:border-slate-700" />,
  a: ({ children, href }: any) => (
    <a href={href} className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

// Message Component - Claude/ChatGPT style (no bubbles for assistant)
function MessageBubble({
  role,
  content,
  isLoading,
  toolCalls,
  isLastAssistant,
  onRegenerate,
}: {
  role: "user" | "assistant";
  content?: string;
  isLoading?: boolean;
  toolCalls?: ToolCall[];
  isLastAssistant?: boolean;
  onRegenerate?: () => void;
}) {
  if (role === "user") {
    // User messages: right-aligned with bubble
    return (
      <div className="flex justify-end mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="max-w-[80%] bg-primary text-primary-foreground px-4 py-3 rounded-2xl rounded-tr-sm text-[15px] leading-relaxed">
          <span className="whitespace-pre-wrap">{content}</span>
        </div>
      </div>
    );
  }

  // Assistant messages: clean text, no bubble (like Claude/ChatGPT)
  return (
    <div className="mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300 group">
      {/* Tool calls indicator */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {toolCalls.map((tc, idx) => (
            <div
              key={idx}
              className="inline-flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-full px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400"
            >
              <Wrench className="w-3 h-3" />
              <span className="font-medium">{tc.name.replace(/_/g, ' ')}</span>
              {tc.result?.status === "success" ? (
                <CheckCircle2 className="w-3 h-3 text-green-500" />
              ) : tc.result?.status === "error" ? (
                <AlertCircle className="w-3 h-3 text-red-500" />
              ) : (
                <Loader2 className="w-3 h-3 animate-spin" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Loading state */}
      {isLoading && !content ? (
        <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"></div>
          </div>
          <span className="text-sm">Thinking...</span>
        </div>
      ) : content ? (
        <>
          <div className="text-[15px]">
            <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
          </div>
          {/* Regenerate button - only on last assistant message */}
          {isLastAssistant && onRegenerate && (
            <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <button
                onClick={onRegenerate}
                className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate response
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

// Suggestion Buttons Component
function SuggestionButtons({ onSelect }: { onSelect: (action: string) => void }) {
  const suggestions = [
    { icon: <Database className="w-4 h-4" />, label: "My Data", action: "What data do I have available?" },
    { icon: <Brain className="w-4 h-4" />, label: "Models", action: "Show me my trained models" },
    { icon: <PlayCircle className="w-4 h-4" />, label: "Train", action: "Help me train a new model" },
    { icon: <FileBarChart className="w-4 h-4" />, label: "Test", action: "Help me test a file" },
    { icon: <Settings2 className="w-4 h-4" />, label: "Help", action: "How does this app work?" },
    { icon: <Sparkles className="w-4 h-4" />, label: "Status", action: "What's the system status?" },
  ];

  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {suggestions.map((s) => (
        <Button
          key={s.label}
          onClick={() => onSelect(s.action)}
          variant="outline"
          size="sm"
          className="gap-2 rounded-full border-slate-300 dark:border-border/50 bg-white dark:bg-transparent hover:bg-slate-100 dark:hover:bg-secondary/60 text-slate-700 dark:text-foreground hover:scale-105 active:scale-95 transition-all duration-200"
        >
          {s.icon}
          <span className="text-xs">{s.label}</span>
        </Button>
      ))}
    </div>
  );
}

// Chat Input Component
function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void;
  disabled?: boolean;
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  return (
    <div className="relative w-full max-w-7xl mx-auto">
      <div className="relative flex items-end gap-2 bg-slate-50 dark:bg-secondary/40 border border-slate-200 dark:border-border/60 rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your data, models, or workflows..."
          className="min-h-[36px] max-h-[150px] py-2 px-3 resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none placeholder:text-muted-foreground/60 text-sm"
          rows={1}
          disabled={disabled}
        />

        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || disabled}
          size="icon"
          className={cn(
            "h-9 w-9 rounded-xl shrink-0 transition-all duration-200",
            input.trim()
              ? "bg-primary text-primary-foreground hover:scale-105"
              : "bg-secondary/60 text-muted-foreground"
          )}
        >
          {disabled ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}

// Storage key for persisting session
const SESSION_STORAGE_KEY = "aryan-senthil-chat-session";

// Main Chat Page Component
export default function ChatPage() {
  const queryClient = useQueryClient();
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => {
    // Load from localStorage on initial render
    if (typeof window !== "undefined") {
      return localStorage.getItem(SESSION_STORAGE_KEY);
    }
    return null;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Track sessions created during streaming (don't fetch these - we have local state)
  const newSessionCreatedRef = useRef<string | null>(null);

  // Fetch sessions
  const { data: sessions = [], refetch: refetchSessions } = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: fetchSessions,
  });

  // Persist session ID to localStorage when it changes
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem(SESSION_STORAGE_KEY, currentSessionId);
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, [currentSessionId]);

  // Load session messages when session changes or on mount
  // BUT skip if this session was just created during streaming (we already have local state)
  useEffect(() => {
    if (currentSessionId) {
      // Skip fetch for sessions we just created - local state is already correct
      if (newSessionCreatedRef.current === currentSessionId) {
        newSessionCreatedRef.current = null;
        return;
      }

      fetchSessionMessages(currentSessionId)
        .then((data) => {
          setMessages(data.messages);
        })
        .catch(() => {
          // Session doesn't exist anymore, clear it
          setCurrentSessionId(null);
          setMessages([]);
        });
    }
  }, [currentSessionId]);

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: (_, deletedId) => {
      refetchSessions();
      if (currentSessionId === deletedId) {
        const remaining = sessions.filter((s) => s.id !== deletedId);
        if (remaining.length > 0) {
          setCurrentSessionId(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    },
  });

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setCurrentToolCalls([]);
    setStreamingContent("");
  };

  const handleSelectSession = (id: string) => {
    if (id !== currentSessionId) {
      setCurrentSessionId(id);
      setCurrentToolCalls([]);
      setStreamingContent("");
    }
  };

  const handleCloseTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteMutation.mutate(id);
  };

  const handleSendMessage = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = { role: "user", content: text };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setCurrentToolCalls([]);
      setStreamingContent("");

      try {
        let newSessionId = currentSessionId;
        let fullContent = "";

        for await (const event of streamChat(text, currentSessionId || undefined)) {
          switch (event.type) {
            case "session":
              newSessionId = event.data.session_id;
              if (!currentSessionId) {
                // Mark this session as created during streaming - don't fetch messages for it
                newSessionCreatedRef.current = newSessionId;
                setCurrentSessionId(newSessionId);
              }
              break;

            case "tool_start":
              setCurrentToolCalls((prev) => [
                ...prev,
                { name: event.data.name, arguments: event.data.arguments },
              ]);
              break;

            case "tool_result":
              setCurrentToolCalls((prev) =>
                prev.map((tc) =>
                  tc.name === event.data.name ? { ...tc, result: event.data.result } : tc
                )
              );
              break;

            case "content":
              fullContent += event.data.content;
              setStreamingContent(fullContent);
              break;

            case "done":
              setMessages((prev) => [...prev, { role: "assistant", content: fullContent }]);
              setStreamingContent("");
              setCurrentToolCalls([]);
              refetchSessions();
              break;

            case "error":
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `Error: ${event.data.message}` },
              ]);
              break;
          }
        }
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${error instanceof Error ? error.message : "Unknown error"}` },
        ]);
      } finally {
        setIsStreaming(false);
      }
    },
    [currentSessionId, refetchSessions]
  );

  const showWelcome = messages.length === 0 && !streamingContent && !isStreaming;

  // Handle regenerate - resend the last user message
  const handleRegenerate = useCallback(() => {
    if (messages.length < 2 || isStreaming) return;

    // Find the last user message
    let lastUserMsgIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        lastUserMsgIndex = i;
        break;
      }
    }

    if (lastUserMsgIndex === -1) return;

    const lastUserMsg = messages[lastUserMsgIndex].content;

    // Remove the last assistant message(s) after the last user message
    setMessages((prev) => prev.slice(0, lastUserMsgIndex));

    // Resend the message
    handleSendMessage(lastUserMsg);
  }, [messages, isStreaming, handleSendMessage]);

  // Get display title for a session
  const getTabTitle = (session: ChatSession) => {
    const title = session.title || "New Session";
    return title.length > 35 ? title.slice(0, 35) + "..." : title;
  };

  return (
    <div className="absolute inset-0 flex flex-col bg-background">
      {/* Chrome-style Tab Bar */}
      <div className="flex items-center bg-secondary/30 border-b border-border px-2 pt-2 gap-1 overflow-x-auto shrink-0">
        {/* New Session Button - On the left */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-lg hover:bg-secondary/80 shrink-0 mr-1"
          onClick={handleNewChat}
          title="New Session"
        >
          <Plus className="w-4 h-4" />
        </Button>

        {/* New Session Tab (when no session selected) */}
        {currentSessionId === null && (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-t-lg bg-background border border-b-0 border-border text-foreground min-w-[140px]"
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0 text-primary" />
            <span className="text-xs truncate">New Session</span>
          </div>
        )}

        {/* Existing Session Tabs */}
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => handleSelectSession(session.id)}
            className={cn(
              "group flex items-center gap-2 px-3 py-2 rounded-t-lg cursor-pointer transition-all min-w-[140px] max-w-[280px] border border-b-0",
              currentSessionId === session.id
                ? "bg-background border-border text-foreground"
                : "bg-secondary/50 border-transparent text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
            )}
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
            <span className="text-xs truncate flex-1">{getTabTitle(session)}</span>
            <button
              onClick={(e) => handleCloseTab(e, session.id)}
              className="opacity-0 group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive rounded p-0.5 transition-all"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}

        {/* Spacer and Status */}
        <div className="flex-1" />
        <div className="flex items-center gap-2 pr-2 shrink-0">
          <Badge variant="outline" className="text-[10px] font-normal">
            GPT-5.1
          </Badge>
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Processing</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-background overflow-hidden">
        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6 py-4">
          <div className="max-w-7xl mx-auto">
            {/* Welcome Message */}
            {showWelcome && (
              <div className="flex flex-col items-center justify-center h-[50vh] max-w-lg mx-auto text-center">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-5">
                  <Bot className="w-6 h-6 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
                  Hi! I'm your AI Assistant
                </h2>
                <p className="text-slate-600 dark:text-slate-400 text-[15px] leading-relaxed">
                  I can help you manage your sensor data, train AI models to detect damage, and test new files. Just ask me anything!
                </p>
              </div>
            )}

            {/* Message History */}
            {messages.map((msg, idx) => {
              // Check if this is the last assistant message
              const isLastAssistant =
                msg.role === "assistant" &&
                idx === messages.length - 1 &&
                !isStreaming;

              return (
                <MessageBubble
                  key={idx}
                  role={msg.role}
                  content={msg.content}
                  isLastAssistant={isLastAssistant}
                  onRegenerate={isLastAssistant ? handleRegenerate : undefined}
                />
              );
            })}

            {/* Streaming Response */}
            {(isStreaming || streamingContent) && (
              <MessageBubble
                role="assistant"
                content={streamingContent}
                isLoading={isStreaming && !streamingContent}
                toolCalls={currentToolCalls}
              />
            )}

            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 border-t border-border/50 bg-background/80 backdrop-blur-sm">
          {(showWelcome || (messages.length > 0 && messages.length < 4)) && !isStreaming && (
            <div className="mb-3 max-w-7xl mx-auto">
              <SuggestionButtons onSelect={handleSendMessage} />
            </div>
          )}
          <ChatInput onSend={handleSendMessage} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
