import React from 'react';
import { Check, X, Clock } from 'lucide-react';

interface TestDataItem {
  test_name: string;
  expected: string;
  actual: string;
  passed: boolean;
  execution_time_ms?: number;
}

interface TestDataTableProps {
  testData: TestDataItem[];
}

export default function TestDataTable({ testData = [] }: TestDataTableProps) {
  if (!testData || testData.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4">No test data available</div>
    );
  }

  const passedCount = testData.filter(t => t.passed).length;
  const failedCount = testData.length - passedCount;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-muted-foreground">Passed: <span className="font-semibold text-foreground">{passedCount}</span></span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <span className="text-muted-foreground">Failed: <span className="font-semibold text-foreground">{failedCount}</span></span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-3 h-3 text-muted-foreground" />
          <span className="text-muted-foreground">
            Total: <span className="font-semibold text-foreground">
              {testData.reduce((acc, t) => acc + (t.execution_time_ms || 0), 0).toFixed(0)}ms
            </span>
          </span>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/50">
              <th className="text-left py-3 px-4 font-semibold text-foreground w-10">Status</th>
              <th className="text-left py-3 px-4 font-semibold text-foreground">Test Name</th>
              <th className="text-left py-3 px-4 font-semibold text-foreground">Expected</th>
              <th className="text-left py-3 px-4 font-semibold text-foreground">Actual</th>
              <th className="text-right py-3 px-4 font-semibold text-foreground w-24">Time</th>
            </tr>
          </thead>
          <tbody>
            {testData.map((test, idx) => (
              <tr key={idx} className={`border-t border-border ${!test.passed ? 'bg-red-500/10' : 'hover:bg-muted/30'}`}>
                <td className="py-3 px-4">
                  {test.passed ? (
                    <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Check className="w-4 h-4 text-green-600" />
                    </div>
                  ) : (
                    <div className="w-6 h-6 rounded-full bg-red-500/20 flex items-center justify-center">
                      <X className="w-4 h-4 text-red-600" />
                    </div>
                  )}
                </td>
                <td className="py-3 px-4 font-medium text-foreground">{test.test_name}</td>
                <td className="py-3 px-4 font-mono text-xs text-muted-foreground">{test.expected}</td>
                <td className={`py-3 px-4 font-mono text-xs ${test.passed ? 'text-muted-foreground' : 'text-red-600 font-medium'}`}>
                  {test.actual}
                </td>
                <td className="py-3 px-4 text-right text-muted-foreground">
                  {test.execution_time_ms?.toFixed(1)}ms
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
