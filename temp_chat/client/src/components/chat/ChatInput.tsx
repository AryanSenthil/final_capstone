import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, Paperclip } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  return (
    <div className="relative max-w-6xl mx-auto w-full">
      <div className="relative flex items-end gap-2 bg-secondary/30 backdrop-blur-sm border border-border rounded-xl p-2 shadow-lg ring-offset-background focus-within:ring-1 focus-within:ring-ring transition-all">
        <Button
          variant="ghost"
          size="icon"
          className="h-10 w-10 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary shrink-0"
          disabled={disabled}
        >
          <Paperclip className="w-5 h-5" />
        </Button>
        
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your data or run a model..."
          className="min-h-[40px] max-h-[200px] py-2.5 resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none placeholder:text-muted-foreground/50"
          rows={1}
          disabled={disabled}
        />

        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || disabled}
          size="icon"
          className={cn(
            "h-10 w-10 rounded-lg shrink-0 transition-all duration-200",
            input.trim() ? "bg-primary text-primary-foreground shadow-glow-primary" : "bg-secondary text-muted-foreground"
          )}
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
      <div className="text-center mt-2">
        <p className="text-[10px] text-muted-foreground opacity-50">
          AI can make mistakes. Verify sensitive data analysis.
        </p>
      </div>
    </div>
  );
}
