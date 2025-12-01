import React, { useState } from 'react';
import { Skeleton } from "@/components/ui/skeleton";
import TestRow from './TestRow';

interface Test {
  test_id: string;
  timestamp: string;
  csv_filename: string;
  model_name: string;
  majority_class: string;
  majority_confidence: number;
  num_chunks: number;
  tags: string[];
  predictions?: string[];
  probabilities?: number[][];
  processing_metadata?: Record<string, unknown>;
  notes?: string;
}

interface TestListProps {
  tests: Test[];
  isLoading: boolean;
  onRerun?: (test: Test) => void;
  onDelete?: (testId: string) => void;
}

export default function TestList({ tests = [], isLoading, onRerun, onDelete }: TestListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleToggle = (testId: string) => {
    setExpandedId(expandedId === testId ? null : testId);
  };

  if (isLoading) {
    return (
      <div className="space-y-1">
        {Array(5).fill(0).map((_, i) => (
          <div key={i} className="flex items-center py-4 px-6 border-b border-border">
            <Skeleton className="h-4 w-20 mr-6" />
            <Skeleton className="h-4 w-32 mr-6" />
            <Skeleton className="h-4 flex-1 mr-6" />
            <Skeleton className="h-4 w-24 mr-6" />
            <Skeleton className="h-4 w-20 mr-6" />
            <Skeleton className="h-4 w-20 mr-6" />
            <Skeleton className="h-6 w-16 mr-6" />
            <Skeleton className="h-4 w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (tests.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-muted-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-1">No tests yet</h3>
        <p className="text-sm text-muted-foreground">Upload a file to run your first inference test</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center py-3 px-6 border-b border-border bg-muted/30">
        <div className="w-24 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider">ID</div>
        <div className="w-36 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Timestamp</div>
        <div className="flex-1 min-w-[180px] pr-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Filename</div>
        <div className="w-40 flex-shrink-0 pr-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Model</div>
        <div className="w-28 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Prediction</div>
        <div className="w-28 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Confidence</div>
        <div className="w-24 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider">Status</div>
        <div className="w-16 flex-shrink-0 text-xs font-semibold text-muted-foreground uppercase tracking-wider text-right">Files</div>
        <div className="w-8 flex-shrink-0"></div>
      </div>

      <div className="divide-y divide-border">
        {tests.map((test) => (
          <TestRow
            key={test.test_id}
            test={test}
            isExpanded={expandedId === test.test_id}
            onToggle={() => handleToggle(test.test_id)}
            onRerun={onRerun}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  );
}
