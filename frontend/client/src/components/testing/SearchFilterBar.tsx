import React from 'react';
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, ArrowUpDown } from "lucide-react";

interface SearchFilterBarProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  modelFilter: string;
  setModelFilter: (model: string) => void;
  statusFilter: string;
  setStatusFilter: (status: string) => void;
  sortBy: string;
  setSortBy: (sort: string) => void;
  models: string[];
}

export default function SearchFilterBar({
  searchQuery,
  setSearchQuery,
  modelFilter,
  setModelFilter,
  statusFilter,
  setStatusFilter,
  sortBy,
  setSortBy,
  models = []
}: SearchFilterBarProps) {
  return (
    <div className="flex items-center gap-4 pb-6 border-b border-border">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search tests..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 h-11 bg-primary/5 border-0 focus:bg-background focus:ring-2 focus:ring-primary transition-all"
        />
      </div>

      <Select value={modelFilter} onValueChange={setModelFilter}>
        <SelectTrigger className="w-44 h-11 bg-primary/5 border-0 focus:ring-2 focus:ring-primary">
          <SelectValue placeholder="All Models" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Models</SelectItem>
          {models.map((model) => (
            <SelectItem key={model} value={model}>{model}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={statusFilter} onValueChange={setStatusFilter}>
        <SelectTrigger className="w-44 h-11 bg-primary/5 border-0 focus:ring-2 focus:ring-primary">
          <SelectValue placeholder="All Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Status</SelectItem>
          <SelectItem value="passed">Passed</SelectItem>
          <SelectItem value="failed">Failed</SelectItem>
          <SelectItem value="warning">Warning</SelectItem>
        </SelectContent>
      </Select>

      <Select value={sortBy} onValueChange={setSortBy}>
        <SelectTrigger className="w-48 h-11 bg-primary/5 border-0 focus:ring-2 focus:ring-primary">
          <ArrowUpDown className="h-4 w-4 mr-2 text-muted-foreground" />
          <SelectValue placeholder="Sort by..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="timestamp-desc">Newest First</SelectItem>
          <SelectItem value="timestamp-asc">Oldest First</SelectItem>
          <SelectItem value="confidence-desc">Highest Confidence</SelectItem>
          <SelectItem value="confidence-asc">Lowest Confidence</SelectItem>
          <SelectItem value="execution-desc">Slowest First</SelectItem>
          <SelectItem value="execution-asc">Fastest First</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
