import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Badge } from "@/components/ui/badge";
import { ChevronDown, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import { format } from 'date-fns';
import ExpandedTestDetails from './ExpandedTestDetails';

interface Test {
  test_id: string;
  timestamp: string;
  csv_filename: string;
  original_csv_path?: string;
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

interface TestRowProps {
  test: Test;
  isExpanded: boolean;
  onToggle: () => void;
  onDelete?: (testId: string) => void;
  onRerun?: (test: Test) => void;
}

export default function TestRow({ test, isExpanded, onToggle, onDelete }: TestRowProps) {
  const confidence = test.majority_confidence || 0;
  const confidenceColor = confidence >= 80
    ? 'text-foreground'
    : confidence >= 50
      ? 'text-muted-foreground'
      : 'text-muted-foreground/50';

  // Determine status based on confidence
  const status = confidence >= 80 ? 'passed' : confidence >= 50 ? 'warning' : 'failed';

  const statusConfig = {
    passed: { icon: CheckCircle, color: 'bg-green-500/10 text-green-600', label: 'Passed' },
    failed: { icon: XCircle, color: 'bg-red-500/10 text-red-600', label: 'Failed' },
    warning: { icon: AlertTriangle, color: 'bg-yellow-500/10 text-yellow-600', label: 'Warning' }
  };

  const statusInfo = statusConfig[status];
  const StatusIcon = statusInfo.icon;

  return (
    <div className="border-b border-border last:border-b-0">
      <div
        onClick={onToggle}
        className="flex items-center py-4 px-6 cursor-pointer hover:bg-muted/30 transition-colors group"
      >
        <div className="w-24 flex-shrink-0">
          <span className="font-mono text-sm text-muted-foreground">{test.test_id.slice(0, 8)}</span>
        </div>

        <div className="w-36 flex-shrink-0">
          <span className="text-sm text-muted-foreground">
            {format(new Date(test.timestamp), 'MMM d, yyyy')}
          </span>
          <span className="text-xs text-muted-foreground/70 ml-2">
            {format(new Date(test.timestamp), 'HH:mm')}
          </span>
        </div>

        <div className="flex-1 min-w-[180px] pr-2 flex flex-col">
          <span className="text-xs font-medium text-foreground truncate" title={test.csv_filename}>
            {test.csv_filename}
          </span>
          {test.original_csv_path && (
            <span className="text-[10px] text-muted-foreground truncate" title={test.original_csv_path}>
              {test.original_csv_path}
            </span>
          )}
        </div>

        <div className="w-40 flex-shrink-0 pr-2">
          <span className="text-sm text-muted-foreground break-all">
            {test.model_name}
          </span>
        </div>

        <div className="w-28 flex-shrink-0">
          <span className="text-sm font-semibold text-foreground">{test.majority_class}</span>
        </div>

        <div className="w-28 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="w-14 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary rounded-full transition-all duration-500"
                style={{ width: `${confidence}%` }}
              />
            </div>
            <span className={`text-sm font-medium ${confidenceColor}`}>
              {confidence?.toFixed(0)}%
            </span>
          </div>
        </div>

        <div className="w-24 flex-shrink-0">
          <Badge variant="secondary" className={`${statusInfo.color} font-medium text-xs`}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusInfo.label}
          </Badge>
        </div>

        <div className="w-16 flex-shrink-0 text-right">
          <span className="text-sm text-muted-foreground">{test.num_chunks}</span>
        </div>

        <div className="w-8 flex-shrink-0 flex justify-end">
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="h-5 w-5 text-muted-foreground group-hover:text-foreground transition-colors" />
          </motion.div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && <ExpandedTestDetails test={test} onDelete={onDelete} />}
      </AnimatePresence>
    </div>
  );
}
