import { ReactNode } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { Bot, User } from 'lucide-react';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content?: string;
  children?: ReactNode;
  isLoading?: boolean;
}

export function MessageBubble({ role, content, children, isLoading }: MessageBubbleProps) {
  return (
    <div className={cn(
      "flex gap-4 max-w-full w-full mx-auto mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300",
      role === 'user' ? "flex-row-reverse" : "flex-row"
    )}>
      {/* Avatar */}
      <Avatar className={cn(
        "h-8 w-8 mt-1 border shadow-sm shrink-0",
        role === 'assistant' 
          ? "bg-primary/10 border-primary/20 text-primary" 
          : "bg-secondary border-border text-secondary-foreground"
      )}>
        <AvatarFallback className="bg-transparent">
          {role === 'assistant' ? <Bot className="w-5 h-5" /> : <User className="w-5 h-5" />}
        </AvatarFallback>
      </Avatar>

      {/* Message Content */}
      <div className={cn(
        "flex-1 min-w-0 space-y-2",
        role === 'user' ? "text-right" : "text-left"
      )}>
        {/* Name & Time (Optional, kept minimal) */}
        <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium px-1">
          {role === 'assistant' ? 'Damage Lab AI' : 'You'}
        </div>

        {/* Bubble / Container */}
        <div className={cn(
          "inline-block rounded-2xl px-4 py-3 text-sm shadow-sm break-words max-w-full",
          role === 'user' 
            ? "bg-primary text-primary-foreground rounded-tr-none" 
            : "bg-transparent text-foreground px-0 py-0 shadow-none"
        )}>
          {isLoading ? (
             <div className="flex items-center gap-2 text-muted-foreground animate-pulse">
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                <span className="ml-2 text-xs font-mono">{content || "Processing..."}</span>
             </div>
          ) : (
            <>
              {content && (
                <p className={cn(
                  "leading-relaxed whitespace-pre-wrap",
                  role === 'assistant' ? "bg-secondary/40 p-4 rounded-lg border border-border/50 rounded-tl-none" : ""
                )}>
                  {content}
                </p>
              )}
              {children && (
                <div className="mt-3 space-y-3 w-full max-w-full overflow-hidden">
                  {children}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
