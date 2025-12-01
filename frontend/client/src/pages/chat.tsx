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

// Markdown components for styling
const markdownComponents = {
  p: ({ children }: any) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }: any) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }: any) => <em className="italic">{children}</em>,
  ul: ({ children }: any) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
  ol: ({ children }: any) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
  li: ({ children }: any) => <li className="ml-2">{children}</li>,
  code: ({ children }: any) => (
    <code className="bg-secondary/80 px-1.5 py-0.5 rounded text-xs font-mono">{children}</code>
  ),
  pre: ({ children }: any) => (
    <pre className="bg-secondary/80 p-3 rounded-lg overflow-x-auto my-2 text-xs">{children}</pre>
  ),
  h1: ({ children }: any) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
  h2: ({ children }: any) => <h2 className="text-base font-bold mb-2">{children}</h2>,
  h3: ({ children }: any) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
};

// Message Bubble Component
function MessageBubble({
  role,
  content,
  isLoading,
  toolCalls,
}: {
  role: "user" | "assistant";
  content?: string;
  isLoading?: boolean;
  toolCalls?: ToolCall[];
}) {
  return (
    <div
      className={cn(
        "flex gap-3 max-w-full w-full mb-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
        role === "user" ? "flex-row-reverse" : "flex-row"
      )}
    >
      <div
        className={cn(
          "h-7 w-7 rounded-full flex items-center justify-center shrink-0 border",
          role === "assistant"
            ? "bg-primary/10 border-primary/20 text-primary"
            : "bg-secondary border-border text-secondary-foreground"
        )}
      >
        {role === "assistant" ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
      </div>

      <div className={cn("flex-1 min-w-0", role === "user" ? "text-right" : "text-left")}>
        <div
          className={cn(
            "inline-block rounded-2xl text-sm break-words max-w-[85%]",
            role === "user"
              ? "bg-primary text-primary-foreground px-4 py-2.5 rounded-tr-sm"
              : "bg-transparent text-foreground"
          )}
        >
          {isLoading && !content ? (
            <div className="flex items-center gap-2 text-muted-foreground animate-pulse bg-secondary/50 px-4 py-3 rounded-2xl rounded-tl-sm border border-border/50">
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
              <div className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"></div>
              <span className="ml-1 text-xs">Thinking...</span>
            </div>
          ) : (
            <>
              {toolCalls && toolCalls.length > 0 && (
                <div className="space-y-1.5 mb-2">
                  {toolCalls.map((tc, idx) => (
                    <div
                      key={idx}
                      className="bg-secondary/40 border border-border/50 rounded-lg px-3 py-2 text-xs inline-flex items-center gap-2"
                    >
                      <Wrench className="w-3 h-3 text-muted-foreground" />
                      <span className="font-mono text-muted-foreground">{tc.name}</span>
                      {tc.result?.status === "success" ? (
                        <CheckCircle2 className="w-3 h-3 text-green-500" />
                      ) : tc.result?.status === "error" ? (
                        <AlertCircle className="w-3 h-3 text-red-500" />
                      ) : (
                        <Loader2 className="w-3 h-3 animate-spin text-muted-foreground" />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {content && (
                <div
                  className={cn(
                    "leading-relaxed",
                    role === "assistant"
                      ? "bg-secondary/50 px-4 py-3 rounded-2xl rounded-tl-sm border border-border/50 prose prose-sm dark:prose-invert max-w-none"
                      : ""
                  )}
                >
                  {role === "assistant" ? (
                    <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
                  ) : (
                    <span className="whitespace-pre-wrap">{content}</span>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Suggestion Buttons Component
function SuggestionButtons({ onSelect }: { onSelect: (action: string) => void }) {
  const suggestions = [
    { icon: <Database className="w-4 h-4" />, label: "Datasets", action: "What datasets do we have?" },
    { icon: <Brain className="w-4 h-4" />, label: "Models", action: "Show me all trained models" },
    { icon: <PlayCircle className="w-4 h-4" />, label: "Train", action: "How do I train a new model?" },
    { icon: <FileBarChart className="w-4 h-4" />, label: "Test", action: "Show me recent test results" },
    { icon: <Settings2 className="w-4 h-4" />, label: "Workflow", action: "Give me guidance on the training workflow" },
    { icon: <Sparkles className="w-4 h-4" />, label: "Status", action: "Check the system status" },
  ];

  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {suggestions.map((s) => (
        <Button
          key={s.label}
          onClick={() => onSelect(s.action)}
          variant="outline"
          size="sm"
          className="gap-2 rounded-full border-border/50 hover:bg-secondary/60 text-foreground hover:scale-105 active:scale-95 transition-all duration-200"
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
    <div className="relative w-full max-w-5xl mx-auto">
      <div className="relative flex items-end gap-2 bg-secondary/40 border border-border/60 rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
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
          <div className="max-w-5xl mx-auto">
            {/* Welcome Message */}
            {showWelcome && (
              <div className="flex flex-col items-center justify-center h-[50vh]">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                  <Bot className="w-5 h-5 text-primary" />
                </div>
                <p className="text-foreground text-base">
                  Hello! I'm your Assistant. I can help you manage datasets, train models, and run inference.
                </p>
              </div>
            )}

            {/* Message History */}
            {messages.map((msg, idx) => (
              <MessageBubble key={idx} role={msg.role} content={msg.content} />
            ))}

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
            <div className="mb-3 max-w-5xl mx-auto">
              <SuggestionButtons onSelect={handleSendMessage} />
            </div>
          )}
          <ChatInput onSend={handleSendMessage} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
