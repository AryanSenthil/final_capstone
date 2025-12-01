import { useState, useEffect, useRef } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { loadAllChats, saveChat, deleteChat, createNewChat, generateChatTitle, ChatSession } from '@/lib/chatStorage';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { DatasetCard } from '@/components/cards/DatasetCard';
import { ModelCard } from '@/components/cards/ModelCard';
import { TrainingProgress } from '@/components/cards/TrainingProgress';
import { TrainingResult } from '@/components/cards/TrainingResult';
import { InferenceResultCard } from '@/components/cards/InferenceResult';
import { FileUpload } from '@/components/inputs/FileUpload';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SuggestionButtons } from './SuggestionButtons';
import { ModelGraphsModal } from '@/components/modals/ModelGraphsModal';
import { HistoryPanel } from './HistoryPanel';
import { 
  MOCK_DATASETS, 
  MOCK_MODELS, 
  INITIAL_TRAINING_JOB, 
  MOCK_INFERENCE_RESULT, 
  Dataset, 
  Model, 
  TrainingJob 
} from '@/lib/mockData';

type MessageType = {
  id: string;
  role: 'user' | 'assistant';
  content?: string;
  type?: 'text' | 'dataset-list' | 'model-list' | 'training-progress' | 'training-result' | 'inference-result' | 'file-upload';
  data?: any;
  isLoading?: boolean;
};

export function ChatInterface() {
  const [chats, setChats] = useState<ChatSession[]>(() => {
    const loaded = loadAllChats();
    return loaded.length > 0 ? loaded : [createNewChat()];
  });
  const [currentChatId, setCurrentChatId] = useState<string | null>(() => {
    const loaded = loadAllChats();
    if (loaded.length > 0) {
      return loaded.sort((a, b) => b.timestamp - a.timestamp)[0].id;
    }
    return createNewChat().id;
  });
  const [messages, setMessages] = useState<MessageType[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Welcome to Damage Lab. I can help you analyze sensor data, train classification models, and generate reports. How can I assist you today?',
      type: 'text'
    }
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [trainingJob, setTrainingJob] = useState<TrainingJob | null>(null);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [showGraphsModal, setShowGraphsModal] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-save current chat
  useEffect(() => {
    if (currentChatId && messages.length > 1) {
      const updatedChat: ChatSession = {
        id: currentChatId,
        title: generateChatTitle(messages),
        timestamp: Date.now(),
        messages
      };
      saveChat(updatedChat);
      setChats(chats.map(c => c.id === currentChatId ? updatedChat : c));
    }
  }, [messages, currentChatId]);

  const handleNewChat = () => {
    const newChat = createNewChat();
    newChat.messages = [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Welcome to Damage Lab. I can help you analyze sensor data, train classification models, and generate reports. How can I assist you today?',
        type: 'text'
      }
    ];
    saveChat(newChat);
    setChats([...chats, newChat]);
    setCurrentChatId(newChat.id);
    setMessages(newChat.messages);
    setShowHistory(false);
  };

  const handleSelectChat = (id: string) => {
    const chat = chats.find(c => c.id === id);
    if (chat) {
      setCurrentChatId(id);
      setMessages(chat.messages);
      setShowHistory(false);
    }
  };

  const handleDeleteChat = (id: string) => {
    deleteChat(id);
    const filtered = chats.filter(c => c.id !== id);
    setChats(filtered);
    if (currentChatId === id && filtered.length > 0) {
      handleSelectChat(filtered[0].id);
    }
  };

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, trainingJob?.currentEpoch]);

  // Simulate Training Loop
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (trainingJob && trainingJob.status === 'training') {
      interval = setInterval(() => {
        setTrainingJob(prev => {
          if (!prev) return null;
          
          const nextEpoch = prev.currentEpoch + 1;
          const progress = nextEpoch / prev.totalEpochs;
          
          // Simulate curves
          const newAccuracy = 0.5 + (0.45 * (1 - Math.exp(-3 * progress))) + (Math.random() * 0.02);
          const newLoss = 1.0 - (0.95 * (1 - Math.exp(-3 * progress))) + (Math.random() * 0.02);
          
          const updatedJob = {
            ...prev,
            currentEpoch: nextEpoch,
            accuracy: newAccuracy,
            loss: newLoss,
            progressMessage: `Training epoch ${nextEpoch}/${prev.totalEpochs}...`,
            history: [...prev.history, { epoch: nextEpoch, accuracy: newAccuracy, loss: newLoss }]
          };

          if (nextEpoch >= prev.totalEpochs) {
            updatedJob.status = 'complete';
            handleTrainingComplete(updatedJob);
            clearInterval(interval);
          }
          
          return updatedJob;
        });
      }, 800); // Fast epoch simulation
    }
    
    return () => clearInterval(interval);
  }, [trainingJob?.status]);

  const handleTrainingComplete = (job: TrainingJob) => {
    setMessages(prev => {
        const filtered = prev.filter(m => m.type !== 'training-progress');
        return [...filtered, {
            id: `res_${Date.now()}`,
            role: 'assistant',
            content: 'Training complete. Here is the performance report.',
            type: 'training-result',
            data: job
        }];
    });
    setIsProcessing(false);
    setTrainingJob(null);
  };

  const handleSendMessage = async (text: string) => {
    // Add user message
    const userMsg: MessageType = { id: Date.now().toString(), role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setIsProcessing(true);

    // Simulate basic intent matching
    const lowerText = text.toLowerCase();
    
    setTimeout(() => {
      if (lowerText.includes('dataset') || lowerText.includes('data')) {
        addAssistantMessage('I found 3 datasets available for analysis.', 'dataset-list', MOCK_DATASETS);
      } else if (lowerText.includes('model') && !lowerText.includes('train')) {
        addAssistantMessage('Here are the models currently in your registry.', 'model-list', MOCK_MODELS);
      } else if (lowerText.includes('train')) {
        startTrainingSimulation();
      } else if (lowerText.includes('inference') || lowerText.includes('predict') || lowerText.includes('test')) {
        // Ask for file upload first
        addAssistantMessage('Please upload the CSV file you want to analyze.', 'file-upload');
      } else {
        addAssistantMessage("I'm not sure about that. Try asking to list datasets, view models, or start a training job.");
      }
    }, 1500);
  };

  const startTrainingSimulation = () => {
     setMessages(prev => [...prev, {
        id: 'training-progress',
        role: 'assistant',
        type: 'training-progress',
        isLoading: true,
        content: 'Initializing training environment...'
     }]);
     
     setTimeout(() => {
        setTrainingJob({...INITIAL_TRAINING_JOB, status: 'training'});
     }, 2000);
  };
  
  const handleFileUploadComplete = (fileName: string) => {
    // Remove upload prompt or just append success
    setMessages(prev => [...prev, {
        id: `upload_success_${Date.now()}`,
        role: 'user',
        content: `Uploaded ${fileName}`
    }]);
    
    setIsProcessing(true);
    
    setTimeout(() => {
         addAssistantMessage(`Analyzing ${fileName} with Anomaloy_Detector_V2...`, 'inference-result', MOCK_INFERENCE_RESULT);
    }, 2000);
  };

  const addAssistantMessage = (content: string, type: MessageType['type'] = 'text', data?: any) => {
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'assistant',
      content,
      type,
      data
    }]);
    setIsProcessing(false);
  };

  const handleQuickAction = (action: string) => {
      handleSendMessage(action);
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans">
      <Sidebar
        chats={chats}
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
      />
      
      <main className="flex-1 flex flex-col h-full relative scientific-grid">
        {/* Header with History Toggle */}
        <div className="h-14 border-b border-border flex items-center px-4 lg:px-8 bg-secondary/5">
          <button 
            onClick={() => setShowHistory(!showHistory)}
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            data-testid="btn-toggle-history"
          >
            ☰ History
          </button>
        </div>

        {/* Chat Area */}
        <ScrollArea className="flex-1 p-4 lg:p-8">
          <div className="max-w-6xl mx-auto pb-20">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} role={msg.role} content={msg.content} isLoading={msg.isLoading && !trainingJob}>
                
                {msg.type === 'dataset-list' && (
                  <div className="grid gap-3 mt-2">
                    {msg.data.map((ds: Dataset) => (
                      <DatasetCard key={ds.id} dataset={ds} />
                    ))}
                  </div>
                )}

                {msg.type === 'model-list' && (
                  <div className="flex gap-3 mt-2 overflow-x-auto pb-2 snap-x snap-mandatory">
                    {msg.data.map((m: Model) => (
                      <div key={m.id} className="flex-shrink-0 w-80 snap-center">
                        <ModelCard model={m} onViewGraphs={(model) => { setSelectedModel(model); setShowGraphsModal(true); }} />
                      </div>
                    ))}
                  </div>
                )}

                {msg.type === 'file-upload' && (
                    <div className="mt-4">
                        <FileUpload onUploadComplete={handleFileUploadComplete} />
                    </div>
                )}

                {msg.type === 'training-progress' && trainingJob && (
                   <TrainingProgress job={trainingJob} onCancel={() => setTrainingJob(null)} />
                )}

                {msg.type === 'training-result' && (
                   <TrainingResult job={msg.data} />
                )}

                {msg.type === 'inference-result' && (
                   <InferenceResultCard result={msg.data} onRunAgain={() => handleSendMessage('Run inference again')} />
                )}

              </MessageBubble>
            ))}
            
            {isProcessing && !messages.some(m => m.isLoading) && (
               <MessageBubble role="assistant" isLoading={true} />
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 lg:p-6 bg-gradient-to-t from-background via-background to-transparent z-10 space-y-4">
          {messages.length === 1 && (
            <SuggestionButtons onSelect={handleSendMessage} />
          )}
          <ChatInput onSend={handleSendMessage} disabled={isProcessing || !!trainingJob} />
        </div>
      </main>

      <ModelGraphsModal model={selectedModel} isOpen={showGraphsModal} onClose={() => setShowGraphsModal(false)} />
      
      {showHistory && (
        <HistoryPanel
          chats={chats}
          currentChatId={currentChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
}
