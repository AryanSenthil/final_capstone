import { MessageCircle, Plus, Trash2, ChevronLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ChatSession } from '@/lib/chatStorage';
import { cn } from '@/lib/utils';

interface HistoryPanelProps {
  chats: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onClose: () => void;
}

export function HistoryPanel({ chats, currentChatId, onNewChat, onSelectChat, onDeleteChat, onClose }: HistoryPanelProps) {
  const sortedChats = [...chats].sort((a, b) => b.timestamp - a.timestamp);

  return (
    <div className="fixed inset-0 z-40 flex">
      <div className="w-full max-w-sm bg-card border-r border-border flex flex-col h-full shadow-lg animate-in slide-in-from-left">
        <div className="h-14 flex items-center justify-between px-4 border-b border-border">
          <h2 className="font-display font-semibold text-foreground">Chat History</h2>
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>

        <Button
          onClick={onNewChat}
          className="m-3 gap-2 bg-primary text-primary-foreground hover:bg-primary/90"
          data-testid="btn-new-chat"
        >
          <Plus className="w-4 h-4" /> New Chat
        </Button>

        <ScrollArea className="flex-1 px-2">
          <div className="space-y-1">
            {sortedChats.length === 0 ? (
              <p className="text-xs text-muted-foreground p-3 text-center">No chat history</p>
            ) : (
              sortedChats.map((chat) => (
                <div
                  key={chat.id}
                  className={cn(
                    'group relative flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-foreground transition-all hover:bg-secondary/40 cursor-pointer',
                    currentChatId === chat.id ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'
                  )}
                  onClick={() => onSelectChat(chat.id)}
                  data-testid={`btn-chat-history-${chat.id}`}
                >
                  <MessageCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="flex-1 truncate text-xs">{chat.title}</span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteChat(chat.id);
                    }}
                    data-testid={`btn-delete-chat-${chat.id}`}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Backdrop */}
      <div className="flex-1 bg-black/20 backdrop-blur-sm" onClick={onClose} />
    </div>
  );
}
