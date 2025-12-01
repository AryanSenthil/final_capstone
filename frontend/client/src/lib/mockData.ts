// Type definitions for API responses

export interface Dataset {
  id: string;
  label: string;
  name: string; // Alias for label for backwards compatibility
  chunks: number;
  fileCount: number; // Alias for chunks for backwards compatibility
  measurement: string;
  unit: string;
  durationPerChunk: string;
  lastUpdated: string;
  samplesPerChunk: number;
  totalDuration: string;
  timeInterval: string;
  folderSize: string;
  sourceFile: string;
  interpolationInterval: string;
  stats: {
    min: number;
    max: number;
    rate: string;
  };
  description?: string;
  category: string;
  qualityScore: number;
  suggestedArchitecture: string;
}

export interface DataPoint {
  time: number;
  value: number;
}

export interface ChunkData {
  label: string;
  measurement_type: string;
  data: DataPoint[];
}

export interface RawFolder {
  name: string;
  path: string;
  fileCount: number;
  totalSize: string;
  imported: string;
}
