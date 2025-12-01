# Carbon Fiber Sensor Data Management Interface

> Advanced AI-powered platform for carbon fiber composite damage detection and analysis

<div align="center">

![TensorFlow](https://img.shields.io/badge/TensorFlow-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)

</div>

## Overview

A full-stack AI platform for carbon fiber composite analysis, featuring deep learning models for damage detection, real-time sensor data processing, and an AI-powered research assistant.

### Key Features

- **Deep Learning Models**: CNN and ResNet architectures for damage classification
- **GPU Acceleration**: CUDA-enabled TensorFlow for high-performance training
- **AI Research Assistant**: OpenAI GPT-5.1 integration for technical support
- **Real-time Processing**: Async FastAPI backend with streaming capabilities
- **Interactive Visualizations**: Comprehensive graphs and metrics using Plotly/Recharts
- **Model Management**: Training, testing, and inference pipelines with TensorBoard

## Tech Stack

**Backend**
- TensorFlow 2.x with CUDA support
- FastAPI + Uvicorn (async web framework)
- scikit-learn, NumPy, Pandas (data science stack)
- OpenAI GPT-5.1 (AI assistant)
- Jupyter Lab (research notebooks)

**Frontend**
- React 19 + TypeScript
- Vite + Express
- Recharts (data visualization)
- Radix UI + Tailwind CSS
- TanStack Query (state management)

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- NVIDIA GPU (optional, for training)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd final_capstone
```

2. **Backend Setup**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup**
```bash
cd frontend
npm install
```

4. **Environment Configuration**
```bash
# Create backend/.env from backend/.env.example
cp backend/.env.example backend/.env
# Add your OpenAI API key to backend/.env
```

### Running the Application

**Option 1: Using the dev script (recommended)**
```bash
./dev.sh
```

**Option 2: Manual start**
```bash
# Terminal 1 - Backend
cd backend && .venv/bin/uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend && npm run dev
```

Access the application at `http://localhost:5000`

## Project Structure

```
.
├── backend/
│   ├── agent/              # AI research assistant
│   ├── training/           # ML model training pipelines
│   ├── testing/            # Model inference & evaluation
│   ├── database/           # Processed sensor data
│   ├── graphs/             # Data visualization generators
│   └── api.py             # FastAPI application
├── frontend/
│   ├── client/src/
│   │   ├── components/    # React components
│   │   ├── pages/         # Application routes
│   │   └── lib/           # Utilities & API client
│   └── server/            # Express + Vite dev server
└── dev.sh                 # Development startup script
```

## Features

### Training Module
- Upload and preprocess sensor data
- Configure CNN/ResNet architectures
- GPU-accelerated training with TensorBoard
- Real-time training metrics and visualizations

### Testing Module
- Batch inference on test datasets
- Performance metrics and confusion matrices
- Export results to CSV/Excel

### AI Research Assistant
- Context-aware technical support
- Integrated with training/testing workflows
- Streaming responses for real-time interaction

### Reports
- Automated PDF generation
- Training history and model performance
- Comprehensive data visualizations

## API Endpoints

- `GET /api/labels` - Available damage classes
- `POST /api/training/start` - Initiate model training
- `POST /api/testing/infer` - Run inference on test data
- `POST /api/chat` - AI assistant interaction
- `GET /api/graphs` - Generate visualization data

## License

This project is licensed under a **Research and Educational License**. See [LICENSE](LICENSE) for details.

**For commercial use, please contact the authors.**

## Authors

Built with ❤️ for advancing carbon fiber composite research

---

**Note**: This is a research project developed for educational purposes. GPU acceleration requires NVIDIA CUDA-compatible hardware and drivers.
