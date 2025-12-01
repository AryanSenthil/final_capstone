import React from 'react';
import { Button } from "@/components/ui/button";
import { Plus, Database, HardDrive, Cpu, CheckCircle, XCircle, Clock } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface Stats {
  totalTests: number;
  storageUsed: number;
  uniqueModels: number;
  passedTests: number;
  failedTests: number;
  avgExecutionTime: number;
}

interface StatsPanelProps {
  stats: Stats;
  isLoading: boolean;
  onTestNewFile: () => void;
}

export default function StatsPanel({
  stats,
  isLoading,
  onTestNewFile
}: StatsPanelProps) {
  const {
    totalTests = 0,
    storageUsed = 0,
    uniqueModels = 0,
    passedTests = 0,
    failedTests = 0,
    avgExecutionTime = 0
  } = stats || {};

  const passRate = totalTests > 0 ? ((passedTests / totalTests) * 100).toFixed(1) : "0";

  return (
    <div className="space-y-6">
      <Button
        variant="default"
        onClick={onTestNewFile}
        aria-label="Test new file"
        className="w-full h-14 font-semibold text-base shadow-lg"
      >
        <Plus className="h-5 w-5 mr-2" />
        Test New File
      </Button>

      <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Overview</h3>
        </div>

        <div className="divide-y divide-border">
          <div className="p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
                <Database className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Total Tests</span>
            </div>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <span className="text-2xl font-bold text-foreground">{totalTests}</span>
            )}
          </div>

          <div className="p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
                <HardDrive className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Storage Used</span>
            </div>
            {isLoading ? (
              <Skeleton className="h-8 w-20" />
            ) : (
              <span className="text-2xl font-bold text-foreground">
                {storageUsed >= 1024
                  ? `${(storageUsed / 1024).toFixed(1)} GB`
                  : `${storageUsed.toFixed(1)} MB`}
              </span>
            )}
          </div>

          <div className="p-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
                <Cpu className="h-5 w-5 text-primary" />
              </div>
              <span className="text-sm text-muted-foreground">Unique Models</span>
            </div>
            {isLoading ? (
              <Skeleton className="h-8 w-12" />
            ) : (
              <span className="text-2xl font-bold text-foreground">{uniqueModels}</span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Test Results</h3>
        </div>

        <div className="p-5 space-y-4">
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Pass Rate</span>
                <span className="text-2xl font-bold text-foreground">{passRate}%</span>
              </div>

              <div className="h-3 bg-muted rounded-full overflow-hidden flex">
                <div
                  className="bg-green-500 transition-all duration-500"
                  style={{ width: `${passRate}%` }}
                />
                <div
                  className="bg-red-500 transition-all duration-500"
                  style={{ width: `${100 - parseFloat(passRate)}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-sm pt-2">
                <div className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-muted-foreground">Passed</span>
                  <span className="font-semibold text-foreground">{passedTests}</span>
                </div>
                <div className="flex items-center gap-2">
                  <XCircle className="w-4 h-4 text-red-600" />
                  <span className="text-muted-foreground">Failed</span>
                  <span className="font-semibold text-foreground">{failedTests}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="bg-card rounded-2xl border border-border shadow-sm overflow-hidden">
        <div className="p-5 border-b border-border flex items-center gap-2">
          <Clock className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Performance</h3>
        </div>

        <div className="p-5">
          {isLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : (
            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-1">Avg. Execution Time</p>
              <p className="text-3xl font-bold text-foreground">
                {avgExecutionTime.toFixed(0)}<span className="text-lg font-normal text-muted-foreground">ms</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
