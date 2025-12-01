
export interface Dataset {
  id: string;
  name: string;
  chunkCount: number;
  qualityScore: number; // 0-100
  description: string;
  dateAdded: string;
}

export interface Model {
  id: string;
  name: string;
  accuracy: number;
  loss: number;
  architecture: string;
  trainingDate: string;
  status: 'ready' | 'training' | 'failed';
}

export interface TrainingJob {
  id: string;
  modelId: string;
  status: 'preparing' | 'training' | 'complete' | 'error';
  currentEpoch: number;
  totalEpochs: number;
  accuracy: number;
  loss: number;
  progressMessage: string;
  history: { epoch: number; accuracy: number; loss: number }[];
}

export interface InferenceResult {
  id: string;
  prediction: string;
  confidence: number;
  chunks: {
    id: string;
    timestamp: string;
    prediction: string;
    confidence: number;
  }[];
}

export const MOCK_DATASETS: Dataset[] = [
  {
    id: 'ds_1',
    name: 'CrushCore_2024_V1',
    chunkCount: 12450,
    qualityScore: 98,
    description: 'High-frequency vibration data from crush core sensors.',
    dateAdded: '2024-05-12',
  },
  {
    id: 'ds_2',
    name: 'Disbond_Calibration_Set',
    chunkCount: 8500,
    qualityScore: 92,
    description: 'Baseline disbond events for calibration.',
    dateAdded: '2024-06-01',
  },
  {
    id: 'ds_3',
    name: 'Noise_Background_Q3',
    chunkCount: 25000,
    qualityScore: 85,
    description: 'Background noise samples for robust training.',
    dateAdded: '2024-06-15',
  },
];

export const MOCK_MODELS: Model[] = [
  {
    id: 'mod_1',
    name: 'Vibration_Classifier_Alpha',
    accuracy: 94.5,
    loss: 0.045,
    architecture: 'ResNet-18 (Modified)',
    trainingDate: '2024-10-01',
    status: 'ready',
  },
  {
    id: 'mod_2',
    name: 'Anomaly_Detector_V2',
    accuracy: 88.2,
    loss: 0.12,
    architecture: 'Autoencoder',
    trainingDate: '2024-11-15',
    status: 'ready',
  },
];

export const INITIAL_TRAINING_JOB: TrainingJob = {
  id: 'job_123',
  modelId: 'mod_new',
  status: 'preparing',
  currentEpoch: 0,
  totalEpochs: 50,
  accuracy: 0,
  loss: 1,
  progressMessage: 'Initializing training environment...',
  history: [],
};

export const MOCK_INFERENCE_RESULT: InferenceResult = {
  id: 'inf_1',
  prediction: 'CRITICAL DISBOND',
  confidence: 0.98,
  chunks: Array.from({ length: 5 }).map((_, i) => ({
    id: `chk_${i}`,
    timestamp: `00:0${i}:45`,
    prediction: i === 2 ? 'NOISE' : 'DISBOND',
    confidence: i === 2 ? 0.45 : 0.96,
  })),
};
