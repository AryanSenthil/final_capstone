import { useState } from "react";
import { ChevronLeft, ChevronRight, Download, ImageIcon, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

// Import placeholder assets
import accuracyImg from "@assets/generated_images/line_chart_showing_training_accuracy_increasing_over_epochs.png";
import lossImg from "@assets/generated_images/line_chart_showing_training_loss_decreasing_over_epochs.png";
import matrixImg from "@assets/generated_images/confusion_matrix_heatmap_visualization.png";

interface GraphData {
  accuracy?: string;
  loss?: string;
  confusion_matrix?: string;
}

interface GraphCarouselProps {
  hasData: boolean;
  graphs?: GraphData;
}

export function GraphCarousel({ hasData, graphs }: GraphCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Use real graphs if provided, otherwise use placeholders
  const slides = [
    {
      id: 'accuracy',
      title: 'Training Accuracy',
      img: graphs?.accuracy ? `data:image/png;base64,${graphs.accuracy}` : accuracyImg,
      desc: 'Validation accuracy over epochs'
    },
    {
      id: 'loss',
      title: 'Loss Function',
      img: graphs?.loss ? `data:image/png;base64,${graphs.loss}` : lossImg,
      desc: 'Cross-entropy loss minimization'
    },
    {
      id: 'matrix',
      title: 'Confusion Matrix',
      img: graphs?.confusion_matrix ? `data:image/png;base64,${graphs.confusion_matrix}` : matrixImg,
      desc: 'Class-wise prediction performance'
    },
  ];

  const nextSlide = () => {
    setCurrentIndex((prev) => (prev + 1) % slides.length);
  };

  const prevSlide = () => {
    setCurrentIndex((prev) => (prev - 1 + slides.length) % slides.length);
  };

  const handleDownload = () => {
    const slide = slides[currentIndex];
    const link = document.createElement('a');
    link.href = slide.img;
    link.download = `${slide.id}_chart.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!hasData) {
    return (
      <div className="h-full min-h-[500px] flex flex-col items-center justify-center bg-gradient-to-b from-background to-muted/20 rounded-3xl border-2 border-dashed border-muted/60 text-muted-foreground p-12 relative overflow-hidden group">
        {/* Background decoration */}
        <div className="absolute inset-0 bg-grid-slate-200/50 [mask-image:linear-gradient(0deg,white,transparent)] dark:bg-grid-slate-800/50 pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center text-center space-y-4">
           <div className="bg-white dark:bg-zinc-800 p-6 rounded-2xl shadow-xl shadow-black/5 ring-1 ring-black/5 group-hover:scale-105 transition-transform duration-500">
             <ImageIcon size={64} className="text-muted-foreground/50" />
           </div>
           <div className="space-y-2 max-w-sm">
             <h3 className="text-xl font-semibold text-foreground tracking-tight">Awaiting Training Data</h3>
             <p className="text-sm text-muted-foreground/80 leading-relaxed">
               Configure your experiment on the left and start a training run to visualize real-time metrics here.
             </p>
           </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between px-1">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">{slides[currentIndex].title}</h2>
          <p className="text-sm text-muted-foreground">{slides[currentIndex].desc}</p>
        </div>
        <div className="flex gap-2">
           <Button variant="outline" size="icon" className="rounded-full hover:bg-secondary transition-colors">
             <Maximize2 size={16} />
           </Button>
           <Button variant="default" size="sm" className="rounded-full gap-2 shadow-sm" onClick={handleDownload}>
             <Download size={14} />
             Export
           </Button>
        </div>
      </div>

      <div className="relative flex-1 bg-white dark:bg-zinc-900/50 rounded-3xl overflow-hidden border border-border shadow-2xl shadow-primary/5 group ring-4 ring-background">
        {/* Navigation Buttons - Floating glass pills */}
        <div className="absolute left-6 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-all duration-300 -translate-x-4 group-hover:translate-x-0">
           <button
             onClick={prevSlide}
             className="p-3 rounded-full bg-white/90 dark:bg-zinc-800/90 backdrop-blur-md shadow-lg border border-border hover:scale-110 transition-all active:scale-95"
           >
             <ChevronLeft size={24} />
           </button>
        </div>

        <div className="absolute right-6 top-1/2 -translate-y-1/2 z-20 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-4 group-hover:translate-x-0">
           <button
             onClick={nextSlide}
             className="p-3 rounded-full bg-white/90 dark:bg-zinc-800/90 backdrop-blur-md shadow-lg border border-border hover:scale-110 transition-all active:scale-95"
           >
             <ChevronRight size={24} />
           </button>
        </div>

        {/* Image Content */}
        <div className="w-full h-full flex items-center justify-center p-12 bg-dot-pattern">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentIndex}
              initial={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }}
              animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
              exit={{ opacity: 0, scale: 1.05, filter: "blur(10px)" }}
              transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
              className="relative w-full h-full flex items-center justify-center"
            >
              <img
                src={slides[currentIndex].img}
                alt={slides[currentIndex].title}
                className="max-h-full max-w-full object-contain drop-shadow-2xl"
              />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Indicators */}
        <div className="absolute bottom-6 left-0 right-0 flex justify-center gap-3 z-20">
          {slides.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentIndex(idx)}
              className={cn(
                "h-2 rounded-full transition-all duration-500 shadow-sm",
                idx === currentIndex
                  ? "bg-primary w-8 scale-100"
                  : "bg-muted-foreground/30 w-2 hover:bg-primary/50 hover:scale-125"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
