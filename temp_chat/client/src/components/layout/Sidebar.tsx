import { Settings, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatSession } from '@/lib/chatStorage';
import { ChatHistory } from './ChatHistory';

interface SidebarProps {
  chats: ChatSession[];
  currentChatId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}

export function Sidebar({ chats, currentChatId, onNewChat, onSelectChat, onDeleteChat }: SidebarProps) {
  return (
    <div className="w-16 lg:w-64 h-full bg-sidebar border-r border-sidebar-border flex flex-col flex-shrink-0 transition-all duration-300">
      <div className="h-16 flex items-center justify-center lg:justify-start lg:px-6 border-b border-sidebar-border">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-primary-foreground font-bold text-xl">D</div>
        <span className="ml-3 font-display font-bold text-lg hidden lg:block text-sidebar-foreground">Damage Lab</span>
      </div>

      <div className="flex-1 flex flex-col overflow-hidden">
      </div>

      <div className="p-4 border-t border-sidebar-border">
        <SidebarButton icon={<Settings />} label="Settings" onClick={() => {}} />
        <div className="mt-2">
            <SidebarButton icon={<LogOut />} label="Logout" onClick={() => {}} variant="destructive" />
        </div>
      </div>
    </div>
  );
}

interface SidebarButtonProps {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  active?: boolean;
  variant?: 'default' | 'destructive';
}

function SidebarButton({ icon, label, onClick, active, variant = 'default' }: SidebarButtonProps) {
  return (
    <Button
      variant="ghost"
      className={`w-full justify-center lg:justify-start h-10 lg:h-11 gap-3 ${
        active 
          ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
          : variant === 'destructive' 
            ? 'text-muted-foreground hover:text-destructive hover:bg-destructive/10' 
            : 'text-muted-foreground hover:text-sidebar-foreground hover:bg-sidebar-accent/50'
      }`}
      onClick={onClick}
      data-testid={`btn-sidebar-${label.toLowerCase().replace(' ', '-')}`}
    >
      {icon}
      <span className="hidden lg:inline">{label}</span>
    </Button>
  );
}
