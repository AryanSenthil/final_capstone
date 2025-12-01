import React, { useState, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { SearchFilterBar, TestList, TestNewFileModal } from '@/components/testing';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface TestSummary {
  test_id: string;
  timestamp: string;
  csv_filename: string;
  model_name: string;
  majority_class: string;
  majority_confidence: number;
  num_chunks: number;
  tags: string[];
}

export default function TestingPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState('');
  const [modelFilter, setModelFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('timestamp-desc');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch tests
  const { data: tests = [], isLoading } = useQuery<TestSummary[]>({
    queryKey: ['/api/tests'],
  });

  // Compute unique models from tests
  const models = useMemo(() => {
    const modelSet = new Set<string>();
    tests.forEach(test => {
      if (test.model_name) modelSet.add(test.model_name);
    });
    return Array.from(modelSet);
  }, [tests]);

  // Filter and sort tests
  const filteredTests = useMemo(() => {
    let result = [...tests];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(test =>
        test.test_id?.toLowerCase().includes(query) ||
        test.csv_filename?.toLowerCase().includes(query) ||
        test.majority_class?.toLowerCase().includes(query) ||
        test.model_name?.toLowerCase().includes(query)
      );
    }

    // Model filter
    if (modelFilter && modelFilter !== 'all') {
      result = result.filter(test => test.model_name === modelFilter);
    }

    // Status filter (based on confidence)
    if (statusFilter && statusFilter !== 'all') {
      result = result.filter(test => {
        const confidence = test.majority_confidence || 0;
        if (statusFilter === 'passed') return confidence >= 80;
        if (statusFilter === 'warning') return confidence >= 50 && confidence < 80;
        if (statusFilter === 'failed') return confidence < 50;
        return true;
      });
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'timestamp-asc':
          return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
        case 'confidence-desc':
          return (b.majority_confidence || 0) - (a.majority_confidence || 0);
        case 'confidence-asc':
          return (a.majority_confidence || 0) - (b.majority_confidence || 0);
        case 'timestamp-desc':
        default:
          return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }
    });

    return result;
  }, [tests, searchQuery, modelFilter, statusFilter, sortBy]);

  const handleSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ['/api/tests'] });
  };

  const handleRerun = async (test: TestSummary) => {
    toast({
      title: "Rerun Test",
      description: `Rerunning test ${test.test_id}...`,
    });
  };

  const handleDelete = async (testId: string) => {
    try {
      const response = await fetch(`/api/tests/${testId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete test');
      }

      toast({
        title: "Test Deleted",
        description: `Test ${testId} has been deleted`,
      });

      queryClient.invalidateQueries({ queryKey: ['/api/tests'] });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete test",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-primary">Inference Testing</h2>
          <p className="text-muted-foreground text-base">Run and analyze model inference on sensor data</p>
        </div>
        <Button
          onClick={() => setIsModalOpen(true)}
          size="lg"
          className="gap-2 shadow-md hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200"
        >
          <Plus className="h-5 w-5" />
          Test New File
        </Button>
      </div>

      {/* Main Content */}
      <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="p-6">
          <SearchFilterBar
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            modelFilter={modelFilter}
            setModelFilter={setModelFilter}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            sortBy={sortBy}
            setSortBy={setSortBy}
            models={models}
          />
        </div>

        <TestList
          tests={filteredTests}
          isLoading={isLoading}
          onRerun={handleRerun}
          onDelete={handleDelete}
        />
      </div>

      <TestNewFileModal
        open={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleSuccess}
      />
    </div>
  );
}
