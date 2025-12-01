import React from 'react';

interface MetadataTableProps {
  metadata: Record<string, unknown>;
}

export default function MetadataTable({ metadata = {} }: MetadataTableProps) {
  const entries = Object.entries(metadata || {});

  if (entries.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4">No metadata available</div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/50">
            <th className="text-left py-3 px-4 font-semibold text-foreground w-1/3">Property</th>
            <th className="text-left py-3 px-4 font-semibold text-foreground">Value</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key} className="border-t border-border hover:bg-muted/30">
              <td className="py-3 px-4 font-medium text-muted-foreground">{key}</td>
              <td className="py-3 px-4 text-foreground font-mono text-xs">
                {typeof value === 'object' ? JSON.stringify(value) : String(value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
