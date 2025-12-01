import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Download, TestTube2, LineChart, Loader2, Trash2, MoreVertical, FileText, Save, X } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from '@/hooks/use-toast';
import RawDataChart from './RawDataChart';

interface RawDataPoint {
  time: number;
  value: number;
}

interface TestDetail {
  test_id: string;
  timestamp: string;
  original_csv_path: string;
  stored_csv_path: string;
  model_path: string;
  model_name: string | null;
  model_version: string | null;
  processing_metadata: Record<string, unknown> | null;
  num_chunks: number;
  predictions: string[] | null;
  probabilities: number[][] | null;
  class_ids: number[] | null;
  majority_class: string | null;
  majority_count: number | null;
  majority_percentage: number | null;
  processed_chunks_dir: string | null;
  auto_detect_csv: boolean;
  csv_structure: Record<string, unknown> | null;
  notes: string | null;
  tags: string[];
}

interface RawDataResponse {
  test_id: string;
  time: number[];
  values: number[];
  time_column: string;
  value_column: string;
  total_points: number;
  sampled_points: number;
}

interface Test {
  test_id: string;
  predictions?: string[];
  probabilities?: number[][];
  processing_metadata?: Record<string, unknown>;
  notes?: string;
}

interface ExpandedTestDetailsProps {
  test: Test;
  onDelete?: (testId: string) => void;
}

export default function ExpandedTestDetails({ test, onDelete }: ExpandedTestDetailsProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [showNotesEditor, setShowNotesEditor] = useState(false);
  const [editedNotes, setEditedNotes] = useState('');

  // Fetch full test details
  const { data: testDetail, isLoading } = useQuery<TestDetail>({
    queryKey: ['/api/tests', test.test_id],
    enabled: !!test.test_id,
  });

  // Fetch raw CSV data for chart
  const { data: rawDataResponse, isLoading: rawDataLoading } = useQuery<RawDataResponse>({
    queryKey: ['/api/tests', test.test_id, 'raw-data'],
    enabled: !!test.test_id,
  });

  const updateNotesMutation = useMutation({
    mutationFn: async (notes: string) => {
      const response = await fetch(`/api/tests/${test.test_id}/notes`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes }),
      });
      if (!response.ok) throw new Error('Failed to update notes');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/tests', test.test_id] });
      queryClient.invalidateQueries({ queryKey: ['/api/tests'] });
      toast({
        title: "Notes Saved",
        description: "Test notes have been updated successfully.",
      });
      setShowNotesEditor(false);
    },
    onError: () => {
      toast({
        title: "Error",
        description: "Failed to save notes.",
        variant: "destructive",
      });
    },
  });

  const handleViewNotes = () => {
    setEditedNotes(testDetail?.notes || test.notes || '');
    setShowNotesEditor(true);
  };

  const handleSaveNotes = () => {
    updateNotesMutation.mutate(editedNotes);
  };

  const handleDownload = () => {
    window.open(`/api/tests/${test.test_id}/csv`, '_blank');
  };

  // Use fetched data or fallback to prop data
  const predictions = testDetail?.predictions || test.predictions || [];
  const probabilities = testDetail?.probabilities || test.probabilities || [];
  const notes = testDetail?.notes || test.notes;

  // Calculate average confidence from all chunks' max probabilities
  const avgConfidence = useMemo(() => {
    if (probabilities.length === 0) return 0;
    const confidences = probabilities.map(probs => {
      if (!probs || probs.length === 0) return 0;
      return Math.max(...probs) * 100;
    });
    return confidences.reduce((a, b) => a + b, 0) / confidences.length;
  }, [probabilities]);

  // Build chart data from raw CSV data
  const chartData: RawDataPoint[] = useMemo(() => {
    if (!rawDataResponse) return [];
    return rawDataResponse.time.map((t, i) => ({
      time: t,
      value: rawDataResponse.values[i]
    }));
  }, [rawDataResponse]);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="overflow-hidden"
    >
      <div className="pt-6 pb-2 px-6 bg-muted/30 border-t border-border">
        {isLoading ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          </div>
        ) : (
          <Tabs defaultValue="predictions" className="w-full">
            <div className="flex items-center justify-between mb-6">
              <TabsList className="bg-background border border-border p-1">
                <TabsTrigger
                  value="predictions"
                  className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground px-4"
                >
                  <TestTube2 className="h-4 w-4 mr-2" />
                  Predictions ({predictions.length})
                </TabsTrigger>
                <TabsTrigger
                  value="chart"
                  className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground px-4"
                >
                  <LineChart className="h-4 w-4 mr-2" />
                  Raw Signal
                </TabsTrigger>
              </TabsList>

              <div className="flex items-center gap-3">
                <Button
                  onClick={handleDownload}
                  variant="default"
                  aria-label="Download CSV file"
                  className="h-10 px-5"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Download CSV
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      aria-label="Test actions menu"
                      className="h-10 px-4"
                    >
                      <MoreVertical className="h-4 w-4 mr-2" />
                      Actions
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-48">
                    <DropdownMenuItem
                      onClick={handleViewNotes}
                      className="gap-2 cursor-pointer focus:bg-primary/10"
                    >
                      <FileText size={16} />
                      {notes ? "View/Edit Notes" : "Add Notes"}
                    </DropdownMenuItem>
                    {onDelete && (
                      <>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => onDelete(test.test_id)}
                          className="gap-2 cursor-pointer text-destructive focus:text-destructive focus:bg-destructive/10"
                        >
                          <Trash2 size={16} />
                          Delete Test
                        </DropdownMenuItem>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <TabsContent value="predictions" className="mt-0">
              <div className="space-y-4">
                {/* Summary stats */}
                {testDetail && (
                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div className="bg-card rounded-lg border border-border p-4">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Files</p>
                      <p className="text-2xl font-bold text-foreground">{testDetail.num_chunks}</p>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-4">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Majority Class</p>
                      <p className="text-2xl font-bold text-foreground">{testDetail.majority_class || 'N/A'}</p>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-4">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Avg Confidence</p>
                      <p className="text-2xl font-bold text-foreground">
                        {avgConfidence.toFixed(0)}%
                      </p>
                    </div>
                    <div className="bg-card rounded-lg border border-border p-4">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">Agreement</p>
                      <p className="text-2xl font-bold text-foreground">
                        {testDetail.majority_count || 0} / {testDetail.num_chunks}
                      </p>
                    </div>
                  </div>
                )}

                {/* Per-file predictions */}
                <div className="overflow-hidden rounded-lg border border-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-muted/50">
                        <th className="text-left py-3 px-4 font-semibold text-foreground">File</th>
                        <th className="text-left py-3 px-4 font-semibold text-foreground">Prediction</th>
                        <th className="text-left py-3 px-4 font-semibold text-foreground">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {predictions.map((pred, idx) => {
                        const probs = probabilities[idx] || [];
                        const maxProb = probs.length > 0 ? Math.max(...probs) * 100 : 0;
                        return (
                          <tr key={idx} className="border-t border-border hover:bg-muted/30">
                            <td className="py-3 px-4 font-medium text-foreground">File {idx + 1}</td>
                            <td className="py-3 px-4">
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary">
                                {pred}
                              </span>
                            </td>
                            <td className="py-3 px-4">
                              <div className="flex items-center gap-3">
                                <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-primary rounded-full"
                                    style={{ width: `${maxProb}%` }}
                                  />
                                </div>
                                <span className="text-sm font-medium text-foreground">
                                  {maxProb.toFixed(0)}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="chart" className="mt-0">
              <div className="bg-card rounded-lg border border-border p-6">
                {rawDataLoading ? (
                  <div className="h-64 flex items-center justify-center">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : chartData.length > 0 ? (
                  <RawDataChart
                    data={chartData}
                    yAxisLabel={rawDataResponse?.value_column || "Value"}
                  />
                ) : (
                  <div className="h-64 flex items-center justify-center text-muted-foreground">
                    No raw data available
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        )}

        {/* Notes Editor Modal */}
        {showNotesEditor && (
          <div className="mt-6 p-4 bg-card rounded-lg border border-border space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
                <FileText size={16} />
                Test Notes
              </h4>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowNotesEditor(false)}
                  aria-label="Cancel editing notes"
                  className="h-8"
                >
                  <X size={14} className="mr-1" />
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleSaveNotes}
                  disabled={updateNotesMutation.isPending}
                  aria-label="Save test notes"
                  className="h-8"
                >
                  {updateNotesMutation.isPending ? (
                    <Loader2 size={14} className="mr-1 animate-spin" />
                  ) : (
                    <Save size={14} className="mr-1" />
                  )}
                  Save Notes
                </Button>
              </div>
            </div>
            <Textarea
              value={editedNotes}
              onChange={(e) => setEditedNotes(e.target.value)}
              placeholder="Add notes about this test..."
              className="min-h-[120px] resize-none"
            />
          </div>
        )}

        {/* Display existing notes when not editing */}
        {!showNotesEditor && notes && (
          <div
            className="mt-6 p-4 bg-card rounded-lg border border-border cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={handleViewNotes}
          >
            <h4 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
              <FileText size={14} />
              Notes
              <span className="text-xs text-muted-foreground font-normal">(click to edit)</span>
            </h4>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{notes}</p>
          </div>
        )}
      </div>
    </motion.div>
  );
}
