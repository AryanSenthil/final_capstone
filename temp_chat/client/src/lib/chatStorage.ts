export interface ChatSession {
  id: string;
  title: string;
  timestamp: number;
  messages: any[];
}

const STORAGE_KEY = 'damage-lab-chats';

export function loadAllChats(): ChatSession[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export function saveChat(session: ChatSession): void {
  try {
    const chats = loadAllChats();
    const index = chats.findIndex(c => c.id === session.id);
    if (index >= 0) {
      chats[index] = session;
    } else {
      chats.push(session);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch (e) {
    console.error('Failed to save chat', e);
  }
}

export function deleteChat(id: string): void {
  try {
    const chats = loadAllChats().filter(c => c.id !== id);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
  } catch (e) {
    console.error('Failed to delete chat', e);
  }
}

export function createNewChat(): ChatSession {
  return {
    id: Date.now().toString(),
    title: 'New Chat',
    timestamp: Date.now(),
    messages: []
  };
}

export function generateChatTitle(messages: any[]): string {
  const firstUserMsg = messages.find(m => m.role === 'user');
  if (firstUserMsg?.content) {
    return firstUserMsg.content.substring(0, 30) + (firstUserMsg.content.length > 30 ? '...' : '');
  }
  return 'New Chat';
}
