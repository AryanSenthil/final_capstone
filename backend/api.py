"""
FastAPI server for the Damage Lab sensor data application.
Provides REST API endpoints for the React frontend.
"""

import json
import os
import zipfile
import io
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

from settings.constants import BACKEND_DIR, DATABASE_DIR, RAW_DATABASE_DIR, MODELS_DIR, REPORTS_DIR, METADATA_FILENAME, OPENAI_MODEL
from settings_api import router as settings_router
from chat_api import router as chat_router

# Load environment variables
load_dotenv()

# Thread lock for training jobs (prevents race conditions)
_training_jobs_lock = threading.Lock()

# Initialize OpenAI client with validation
_openai_api_key = os.getenv("OPENAI_API_KEY")
if not _openai_api_key:
    print("[WARNING] OPENAI_API_KEY not set. AI features will use fallback behavior.")
    openai_client = None
else:
    openai_client = OpenAI(api_key=_openai_api_key)


def _safe_openai_call(func, fallback_value, error_prefix="OpenAI API"):
    """
    Safely execute an OpenAI API call with proper error handling.
    Returns fallback_value if call fails.
    """
    if openai_client is None:
        print(f"[INFO] {error_prefix}: API key not configured, using fallback")
        return fallback_value
    try:
        return func()
    except Exception as e:
        error_msg = str(e)
        # Provide user-friendly error messages
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            print(f"[ERROR] {error_prefix}: Invalid API key. Please check your OPENAI_API_KEY.")
        elif "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
            print(f"[ERROR] {error_prefix}: Rate limit reached. Please wait and try again.")
        elif "timeout" in error_msg.lower():
            print(f"[ERROR] {error_prefix}: Request timed out. The AI service may be slow.")
        else:
            print(f"[ERROR] {error_prefix}: {error_msg}")
        return fallback_value

app = FastAPI(
    title="Damage Lab API",
    description="API for sensor data visualization and management",
    version="1.0.0"
)

# CORS middleware for frontend development and production
# Allow all origins for internal lab deployment flexibility
# In production, the frontend proxy handles most requests, so CORS is mainly for direct API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for EC2 deployment flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(settings_router)
app.include_router(chat_router)


# ============ Pydantic Models ============

class DatasetStats(BaseModel):
    min: float
    max: float
    rate: str


class Dataset(BaseModel):
    id: str
    label: str
    chunks: int
    measurement: str
    unit: str
    durationPerChunk: str
    lastUpdated: str
    samplesPerChunk: int
    totalDuration: str
    timeInterval: str
    folderSize: str
    sourceFile: str
    interpolationInterval: str
    stats: DatasetStats
    # AI-generated fields (optional)
    description: Optional[str] = None
    category: Optional[str] = None
    qualityScore: Optional[float] = None
    suggestedArchitecture: Optional[str] = None


class DataPoint(BaseModel):
    time: float
    value: float


class FileDataResponse(BaseModel):
    data: list[DataPoint]
    yAxisLabel: str


class FileInfo(BaseModel):
    name: str
    size: str


class RawFolderMetadata(BaseModel):
    importedAt: str
    totalFiles: int
    totalSize: str
    avgSize: str
    largest: str
    smallest: str


class RawFolder(BaseModel):
    id: str
    name: str
    fileCount: int
    size: str
    date: str
    files: list[FileInfo]
    metadata: RawFolderMetadata


class IngestRequest(BaseModel):
    folderPath: str
    classificationLabel: str
    timeInterval: float = 0.1
    chunkDuration: float = 8.0
    padding: float = 1.0


class IngestResponse(BaseModel):
    success: bool
    message: str
    label: Optional[str] = None
    chunksCreated: Optional[int] = None


class SuggestLabelRequest(BaseModel):
    folderPath: str


class SuggestLabelResponse(BaseModel):
    success: bool
    label: str
    message: Optional[str] = None


class DeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_processed: bool = False
    deleted_raw: bool = False


# ============ Helper Functions ============

def format_file_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def get_folder_size(folder_path: Path) -> int:
    """Calculate total size of all files in a folder."""
    total = 0
    for f in folder_path.iterdir():
        if f.is_file():
            total += f.stat().st_size
    return total


def parse_measurement_type(measurement_type: str) -> tuple[str, str]:
    """Parse measurement type string like 'Current (pA)' into measurement and unit."""
    if "(" in measurement_type and ")" in measurement_type:
        measurement = measurement_type.split("(")[0].strip()
        unit = measurement_type.split("(")[1].replace(")", "").strip()
        return measurement, unit
    return measurement_type, ""


def generate_ai_metadata_for_label(label_id: str) -> dict:
    """Generate AI metadata for a label after data processing.

    This is called automatically after ingestion completes.
    Returns the generated metadata dict or None if generation fails.
    """
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        print(f"[WARN] Cannot generate AI metadata: label directory not found: {label_id}")
        return None

    metadata = load_metadata(label_dir)
    if not metadata:
        print(f"[WARN] Cannot generate AI metadata: metadata.json not found for: {label_id}")
        return None

    # Prepare context for GPT
    processing = metadata.get("processing", {})
    dataset_info = metadata.get("dataset", {})
    stats_info = metadata.get("sample_statistics", {})
    value_range = stats_info.get("value_range", [0, 0])

    context = f"""
Dataset Label: {label_id}
Source Folder: {metadata.get("source_folder", "unknown")}
Data Type: {metadata.get("data_type", "unknown")}
Measurement Type: {metadata.get("measurement_type", "unknown")}

Processing Parameters:
- Interpolation Interval: {processing.get("interpolation_interval", "N/A")}
- Chunk Duration: {processing.get("chunk_duration", "N/A")}s
- Time Length: {processing.get("time_length", "N/A")}s
- Interpolation Method: {processing.get("interpolation", "N/A")}

Dataset Statistics:
- Total Chunks: {dataset_info.get("total_chunks", 0)}
- Samples per Chunk: {dataset_info.get("samples_per_chunk", 0)}
- Source Files Count: {dataset_info.get("source_files_count", 0)}
- Folder Size: {dataset_info.get("folder_size_mb", 0):.2f} MB

Sample Statistics:
- Original Sampling Rate: {stats_info.get("original_sampling_rate", "N/A")}
- Value Range: [{value_range[0] if len(value_range) > 0 else 0}, {value_range[1] if len(value_range) > 1 else 0}]
- Mean: {stats_info.get("value_mean", 0):.4f}
- Std Dev: {stats_info.get("value_std", 0):.4f}
"""

    try:
        client = openai_client

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI assistant specialized in analyzing sensor data datasets for machine learning.
Given dataset metadata, provide:
1. A concise description (2-3 sentences) explaining what this dataset represents
2. A category (e.g., "structural_damage", "material_testing", "vibration_analysis", "electrical_signal", etc.)
3. A quality score (0.0-1.0) based on data completeness, sample size, and statistics
4. A suggested architecture ("CNN" or "ResNet") based on the data characteristics
5. 2-3 training tips specific to this dataset

Respond in JSON format:
{
    "description": "...",
    "category": "...",
    "quality_score": 0.85,
    "suggested_architecture": "CNN",
    "training_tips": ["tip1", "tip2", "tip3"]
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this sensor dataset and provide metadata:\n\n{context}"
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=60.0
        )

        result = json.loads(response.choices[0].message.content)

        # Normalize suggested architecture to only valid values
        suggested_arch = result.get("suggested_architecture", "CNN")
        if suggested_arch and isinstance(suggested_arch, str):
            suggested_arch_upper = suggested_arch.strip().upper()
            if "RESNET" in suggested_arch_upper:
                suggested_arch = "ResNet"
            else:
                suggested_arch = "CNN"
        else:
            suggested_arch = "CNN"

        # Save AI metadata back to the metadata.json file
        metadata["ai_metadata"] = {
            "description": result.get("description", ""),
            "category": result.get("category", ""),
            "quality_score": result.get("quality_score", 0.5),
            "suggested_architecture": suggested_arch,
            "training_tips": result.get("training_tips", []),
            "generated_at": datetime.now().isoformat()
        }

        metadata_path = label_dir / METADATA_FILENAME
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"✓ Generated AI metadata for label: {label_id}")
        return metadata["ai_metadata"]

    except Exception as e:
        print(f"[WARN] Failed to generate AI metadata for {label_id}: {e}")
        return None


def load_metadata(label_dir: Path) -> Optional[dict]:
    """Load metadata.json from a label directory."""
    metadata_path = label_dir / METADATA_FILENAME
    if metadata_path.exists():
        with open(metadata_path) as f:
            return json.load(f)
    return None


def metadata_to_dataset(label: str, metadata: dict, label_dir: Path) -> Dataset:
    """Convert backend metadata to frontend Dataset format."""
    measurement, unit = parse_measurement_type(metadata.get("measurement_type", "Current (pA)"))
    processing = metadata.get("processing", {})
    dataset_info = metadata.get("dataset", {})
    stats_info = metadata.get("sample_statistics", {})
    ai_metadata = metadata.get("ai_metadata", {})

    # Calculate folder size
    folder_size = get_folder_size(label_dir)

    # Parse value range for stats
    value_range = stats_info.get("value_range", [0, 0])

    return Dataset(
        id=label,
        label=label,
        chunks=dataset_info.get("total_chunks", 0),
        measurement=measurement,
        unit=unit,
        durationPerChunk=f"{processing.get('time_length', 10.0)}s",
        lastUpdated=datetime.fromisoformat(metadata.get("generated_at", datetime.now().isoformat())).strftime("%b %d, %Y %H:%M:%S"),
        samplesPerChunk=dataset_info.get("samples_per_chunk", 101),
        totalDuration=f"{processing.get('time_length', 10.0)}s",
        timeInterval=f"{processing.get('interpolation_interval', 0.1)}s",
        folderSize=format_file_size(folder_size),
        sourceFile=metadata.get("source_folder", "unknown"),
        interpolationInterval=f"{processing.get('interpolation_interval', 0.1)}s",
        stats=DatasetStats(
            min=value_range[0] if len(value_range) > 0 else 0,
            max=value_range[1] if len(value_range) > 1 else 0,
            rate=stats_info.get("original_sampling_rate", "N/A")
        ),
        # AI-generated fields
        description=ai_metadata.get("description"),
        category=ai_metadata.get("category"),
        qualityScore=ai_metadata.get("quality_score"),
        suggestedArchitecture=ai_metadata.get("suggested_architecture"),
    )


# ============ API Endpoints ============

@app.get("/")
async def root():
    """API health check."""
    return {"status": "ok", "message": "Damage Lab API is running"}


@app.get("/api/labels", response_model=list[Dataset])
async def get_labels():
    """Get all processed datasets/labels."""
    datasets = []

    if not DATABASE_DIR.exists():
        return datasets

    for label_dir in DATABASE_DIR.iterdir():
        if label_dir.is_dir():
            metadata = load_metadata(label_dir)
            if metadata:
                dataset = metadata_to_dataset(label_dir.name, metadata, label_dir)
                datasets.append(dataset)

    # Sort by lastUpdated (most recent first)
    datasets.sort(key=lambda d: d.lastUpdated, reverse=True)
    return datasets


@app.get("/api/labels/{label_id}", response_model=Dataset)
async def get_label(label_id: str):
    """Get metadata for a specific dataset/label."""
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    metadata = load_metadata(label_dir)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Metadata not found for label '{label_id}'")

    return metadata_to_dataset(label_id, metadata, label_dir)


@app.delete("/api/labels/{label_id}", response_model=DeleteResponse)
async def delete_label(label_id: str, delete_raw: bool = True):
    """Delete a dataset and optionally its raw data."""
    from database_management import delete_dataset

    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    result = delete_dataset(label_id, delete_raw=delete_raw)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])

    return DeleteResponse(
        success=True,
        message=result["message"],
        deleted_processed=result["deleted_processed"],
        deleted_raw=result["deleted_raw"]
    )


class GenerateMetadataResponse(BaseModel):
    success: bool
    description: str
    category: str
    quality_score: float
    suggested_architecture: str
    training_tips: list[str]


@app.post("/api/labels/{label_id}/generate-metadata", response_model=GenerateMetadataResponse)
async def generate_label_metadata(label_id: str):
    """Use GPT to generate AI metadata (description, category, quality score, etc.) for a dataset."""

    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    metadata = load_metadata(label_dir)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Metadata not found for label '{label_id}'")

    # Prepare context for GPT
    processing = metadata.get("processing", {})
    dataset_info = metadata.get("dataset", {})
    stats_info = metadata.get("sample_statistics", {})
    value_range = stats_info.get("value_range", [0, 0])

    context = f"""
Dataset Label: {label_id}
Source Folder: {metadata.get("source_folder", "unknown")}
Data Type: {metadata.get("data_type", "unknown")}
Measurement Type: {metadata.get("measurement_type", "unknown")}

Processing Parameters:
- Interpolation Interval: {processing.get("interpolation_interval", "N/A")}
- Chunk Duration: {processing.get("chunk_duration", "N/A")}s
- Time Length: {processing.get("time_length", "N/A")}s
- Interpolation Method: {processing.get("interpolation", "N/A")}

Dataset Statistics:
- Total Chunks: {dataset_info.get("total_chunks", 0)}
- Samples per Chunk: {dataset_info.get("samples_per_chunk", 0)}
- Source Files Count: {dataset_info.get("source_files_count", 0)}
- Folder Size: {dataset_info.get("folder_size_mb", 0):.2f} MB

Sample Statistics:
- Original Sampling Rate: {stats_info.get("original_sampling_rate", "N/A")}
- Value Range: [{value_range[0] if len(value_range) > 0 else 0}, {value_range[1] if len(value_range) > 1 else 0}]
- Mean: {stats_info.get("value_mean", 0):.4f}
- Std Dev: {stats_info.get("value_std", 0):.4f}
"""

    try:
        client = openai_client

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI assistant specialized in analyzing sensor data datasets for machine learning.
Given dataset metadata, provide:
1. A concise description (2-3 sentences) explaining what this dataset represents
2. A category (e.g., "structural_damage", "material_testing", "vibration_analysis", "electrical_signal", etc.)
3. A quality score (0.0-1.0) based on data completeness, sample size, and statistics
4. A suggested architecture ("CNN" or "ResNet") based on the data characteristics
5. 2-3 training tips specific to this dataset

Respond in JSON format:
{
    "description": "...",
    "category": "...",
    "quality_score": 0.85,
    "suggested_architecture": "CNN",
    "training_tips": ["tip1", "tip2", "tip3"]
}"""
                },
                {
                    "role": "user",
                    "content": f"Analyze this sensor dataset and provide metadata:\n\n{context}"
                }
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Normalize suggested architecture to only valid values
        suggested_arch = result.get("suggested_architecture", "CNN")
        if suggested_arch and isinstance(suggested_arch, str):
            suggested_arch_upper = suggested_arch.strip().upper()
            if "RESNET" in suggested_arch_upper:
                suggested_arch = "ResNet"
            else:
                suggested_arch = "CNN"
        else:
            suggested_arch = "CNN"

        # Save AI metadata back to the metadata.json file
        metadata["ai_metadata"] = {
            "description": result.get("description", ""),
            "category": result.get("category", ""),
            "quality_score": result.get("quality_score", 0.5),
            "suggested_architecture": suggested_arch,
            "training_tips": result.get("training_tips", []),
            "generated_at": datetime.now().isoformat()
        }

        metadata_path = label_dir / METADATA_FILENAME
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        return GenerateMetadataResponse(
            success=True,
            description=result.get("description", ""),
            category=result.get("category", ""),
            quality_score=result.get("quality_score", 0.5),
            suggested_architecture=result.get("suggested_architecture", "CNN"),
            training_tips=result.get("training_tips", [])
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


class BatchGenerateMetadataResponse(BaseModel):
    success: bool
    generated_count: int
    skipped_count: int
    errors: list[str]


@app.post("/api/labels/generate-all-metadata", response_model=BatchGenerateMetadataResponse)
async def generate_all_labels_metadata(force: bool = False):
    """Generate AI metadata for all labels that don't have it yet.

    Args:
        force: If True, regenerate metadata even for labels that already have it.
    """

    if not DATABASE_DIR.exists():
        return BatchGenerateMetadataResponse(
            success=True,
            generated_count=0,
            skipped_count=0,
            errors=[]
        )

    generated_count = 0
    skipped_count = 0
    errors = []

    client = openai_client

    for label_dir in DATABASE_DIR.iterdir():
        if not label_dir.is_dir():
            continue

        label_id = label_dir.name
        metadata = load_metadata(label_dir)

        if not metadata:
            errors.append(f"{label_id}: No metadata.json found")
            continue

        # Skip if already has AI metadata and not forcing
        if not force and metadata.get("ai_metadata"):
            skipped_count += 1
            continue

        try:
            # Prepare context for GPT
            processing = metadata.get("processing", {})
            dataset_info = metadata.get("dataset", {})
            stats_info = metadata.get("sample_statistics", {})
            value_range = stats_info.get("value_range", [0, 0])

            context = f"""
Dataset Label: {label_id}
Source Folder: {metadata.get("source_folder", "unknown")}
Data Type: {metadata.get("data_type", "unknown")}
Measurement Type: {metadata.get("measurement_type", "unknown")}

Processing Parameters:
- Interpolation Interval: {processing.get("interpolation_interval", "N/A")}
- Chunk Duration: {processing.get("chunk_duration", "N/A")}s
- Time Length: {processing.get("time_length", "N/A")}s

Dataset Statistics:
- Total Chunks: {dataset_info.get("total_chunks", 0)}
- Samples per Chunk: {dataset_info.get("samples_per_chunk", 0)}
- Folder Size: {dataset_info.get("folder_size_mb", 0):.2f} MB

Sample Statistics:
- Original Sampling Rate: {stats_info.get("original_sampling_rate", "N/A")}
- Value Range: [{value_range[0] if len(value_range) > 0 else 0}, {value_range[1] if len(value_range) > 1 else 0}]
- Mean: {stats_info.get("value_mean", 0):.4f}
- Std Dev: {stats_info.get("value_std", 0):.4f}
"""

            response = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an AI assistant specialized in analyzing sensor data datasets for machine learning.
Given dataset metadata, provide a JSON response with:
{
    "description": "2-3 sentence description of what this dataset represents",
    "category": "category like structural_damage, material_testing, vibration_analysis, electrical_signal",
    "quality_score": 0.85,
    "suggested_architecture": "CNN or ResNet",
    "training_tips": ["tip1", "tip2"]
}"""
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this sensor dataset:\n\n{context}"
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # Save AI metadata
            metadata["ai_metadata"] = {
                "description": result.get("description", ""),
                "category": result.get("category", ""),
                "quality_score": result.get("quality_score", 0.5),
                "suggested_architecture": result.get("suggested_architecture", "CNN"),
                "training_tips": result.get("training_tips", []),
                "generated_at": datetime.now().isoformat()
            }

            metadata_path = label_dir / METADATA_FILENAME
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            generated_count += 1

        except Exception as e:
            errors.append(f"{label_id}: {str(e)}")

    return BatchGenerateMetadataResponse(
        success=len(errors) == 0,
        generated_count=generated_count,
        skipped_count=skipped_count,
        errors=errors
    )


@app.get("/api/labels/{label_id}/files", response_model=list[FileInfo])
async def get_label_files(label_id: str):
    """Get list of CSV files for a specific dataset/label."""
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    files = []
    for csv_file in sorted(label_dir.glob("*.csv")):
        size = csv_file.stat().st_size
        files.append(FileInfo(
            name=csv_file.stem,  # filename without extension
            size=format_file_size(size)
        ))

    return files


@app.get("/api/labels/{label_id}/files/{filename}", response_model=FileDataResponse)
async def get_file_data(label_id: str, filename: str):
    """Get time-series data from a specific CSV file."""
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    # Try with and without .csv extension
    csv_path = label_dir / f"{filename}.csv"
    if not csv_path.exists():
        csv_path = label_dir / filename

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    try:
        # Read CSV, skipping the first row (classification label)
        df = pd.read_csv(csv_path, skiprows=1)

        # Validate CSV has at least 2 columns
        if len(df.columns) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"CSV file must have at least 2 columns (time and value). Found {len(df.columns)} column(s)."
            )

        # Get column names (should be Time(s) and Current (pA) or similar)
        time_col = df.columns[0]
        value_col = df.columns[1]  # This will be like "Current (pA)"

        data_points = []
        for _, row in df.iterrows():
            try:
                data_points.append(DataPoint(
                    time=float(row[time_col]),
                    value=float(row[value_col])
                ))
            except (ValueError, TypeError):
                # Skip rows with non-numeric data
                continue

        if not data_points:
            raise HTTPException(
                status_code=400,
                detail="No valid numeric data found in file. Please check the CSV format."
            )

        return FileDataResponse(
            data=data_points,
            yAxisLabel=value_col  # Return the actual column header
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="The CSV file is empty.")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.get("/api/labels/{label_id}/files/{filename}/download")
async def download_file(label_id: str, filename: str):
    """Download a single CSV file."""
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    csv_path = label_dir / f"{filename}.csv"
    if not csv_path.exists():
        csv_path = label_dir / filename

    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    return FileResponse(
        path=csv_path,
        filename=f"{filename}.csv",
        media_type="text/csv"
    )


@app.get("/api/labels/{label_id}/download")
async def download_all_files(label_id: str):
    """Download all CSV files for a label as a ZIP."""
    label_dir = DATABASE_DIR / label_id

    if not label_dir.exists():
        raise HTTPException(status_code=404, detail=f"Label '{label_id}' not found")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for csv_file in sorted(label_dir.glob("*.csv")):
            zip_file.write(csv_file, csv_file.name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={label_id}.zip"}
    )


@app.get("/api/raw-database/{folder_id}/download")
async def download_raw_folder(folder_id: str):
    """Download all files from a raw folder as a ZIP."""
    folder_dir = RAW_DATABASE_DIR / folder_id

    if not folder_dir.exists():
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for csv_file in sorted(folder_dir.glob("*.csv")):
            zip_file.write(csv_file, csv_file.name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={folder_id}.zip"}
    )


@app.get("/api/raw-database/{folder_id}/files/{filename}/download")
async def download_raw_file(folder_id: str, filename: str):
    """Download a single file from a raw folder."""
    folder_dir = RAW_DATABASE_DIR / folder_id

    if not folder_dir.exists():
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")

    file_path = folder_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in folder '{folder_id}'")

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=filename
    )


@app.get("/api/raw-database", response_model=list[RawFolder])
async def get_raw_database():
    """Get all raw data folders."""
    folders = []

    if not RAW_DATABASE_DIR.exists():
        return folders

    for folder_dir in RAW_DATABASE_DIR.iterdir():
        if folder_dir.is_dir():
            # Get files in folder
            files = []
            total_size = 0
            file_sizes = []

            for csv_file in sorted(folder_dir.glob("*.csv")):
                size = csv_file.stat().st_size
                total_size += size
                file_sizes.append(size)
                files.append(FileInfo(
                    name=csv_file.name,
                    size=format_file_size(size)
                ))

            # Load metadata if exists
            metadata_path = folder_dir / METADATA_FILENAME
            import_date = datetime.now()
            if metadata_path.exists():
                with open(metadata_path) as f:
                    raw_meta = json.load(f)
                    import_date = datetime.fromisoformat(raw_meta.get("imported_at", datetime.now().isoformat()))

            # Calculate stats
            avg_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
            largest = max(file_sizes) if file_sizes else 0
            smallest = min(file_sizes) if file_sizes else 0

            folders.append(RawFolder(
                id=folder_dir.name,
                name=folder_dir.name,
                fileCount=len(files),
                size=format_file_size(total_size),
                date=import_date.strftime("%b %d, %Y"),
                files=files,
                metadata=RawFolderMetadata(
                    importedAt=import_date.strftime("%b %d, %Y %I:%M %p"),
                    totalFiles=len(files),
                    totalSize=format_file_size(total_size),
                    avgSize=format_file_size(int(avg_size)),
                    largest=format_file_size(largest),
                    smallest=format_file_size(smallest)
                )
            ))

    return folders


class RawUploadResponse(BaseModel):
    success: bool
    folder_name: str
    folder_path: str
    files_uploaded: int
    message: str


@app.post("/api/raw-database/upload", response_model=RawUploadResponse)
async def upload_raw_files(
    files: List[UploadFile] = File(...),
    folder_name: Optional[str] = None
):
    """
    Upload CSV files from client to raw_database for later ingestion.

    This endpoint receives files from the user's local machine and stores them
    in the server's raw_database directory for processing.

    If folder_name is provided, uses that exact name.
    If folder already exists, appends a number suffix to avoid duplicates.
    """
    # Use provided folder name or generate from timestamp
    if folder_name and folder_name.strip():
        base_folder_name = folder_name.strip()
    else:
        base_folder_name = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Sanitize folder name
    base_folder_name = re.sub(r'[^\w\-_.]', '_', base_folder_name)

    # Check if folder already exists - if so, append a number
    folder_name = base_folder_name
    folder_path = RAW_DATABASE_DIR / folder_name
    counter = 2
    while folder_path.exists():
        folder_name = f"{base_folder_name}_{counter}"
        folder_path = RAW_DATABASE_DIR / folder_name
        counter += 1

    # Create folder in raw_database
    folder_path = RAW_DATABASE_DIR / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    saved_files = []
    skipped_files = []

    for file in files:
        # Only accept CSV files
        if not file.filename or not file.filename.lower().endswith('.csv'):
            skipped_files.append(file.filename or "unknown")
            continue

        # Sanitize filename
        safe_filename = re.sub(r'[^\w\-_.]', '_', file.filename)
        file_path = folder_path / safe_filename

        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files.append(safe_filename)
        except Exception as e:
            print(f"[ERROR] Failed to save file {file.filename}: {e}")
            skipped_files.append(file.filename)

    if not saved_files:
        # Clean up empty folder
        if folder_path.exists() and not any(folder_path.iterdir()):
            folder_path.rmdir()
        raise HTTPException(
            status_code=400,
            detail="No valid CSV files were uploaded"
        )

    # Save metadata
    metadata = {
        "imported_at": datetime.now().isoformat(),
        "source": "web_upload",
        "files": saved_files,
        "skipped": skipped_files
    }
    with open(folder_path / METADATA_FILENAME, "w") as f:
        json.dump(metadata, f, indent=2)

    message = f"Successfully uploaded {len(saved_files)} file(s)"
    if skipped_files:
        message += f", skipped {len(skipped_files)} non-CSV file(s)"

    return RawUploadResponse(
        success=True,
        folder_name=folder_name,
        folder_path=str(folder_path),
        files_uploaded=len(saved_files),
        message=message
    )


@app.get("/api/raw-database/{folder_id}", response_model=RawFolder)
async def get_raw_folder(folder_id: str):
    """Get details for a specific raw data folder."""
    folder_dir = RAW_DATABASE_DIR / folder_id

    if not folder_dir.exists():
        raise HTTPException(status_code=404, detail=f"Folder '{folder_id}' not found")

    # Get files in folder
    files = []
    total_size = 0
    file_sizes = []

    for csv_file in sorted(folder_dir.glob("*.csv")):
        size = csv_file.stat().st_size
        total_size += size
        file_sizes.append(size)
        files.append(FileInfo(
            name=csv_file.name,
            size=format_file_size(size)
        ))

    # Load metadata if exists
    metadata_path = folder_dir / METADATA_FILENAME
    import_date = datetime.now()
    if metadata_path.exists():
        with open(metadata_path) as f:
            raw_meta = json.load(f)
            import_date = datetime.fromisoformat(raw_meta.get("imported_at", datetime.now().isoformat()))

    # Calculate stats
    avg_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
    largest = max(file_sizes) if file_sizes else 0
    smallest = min(file_sizes) if file_sizes else 0

    return RawFolder(
        id=folder_dir.name,
        name=folder_dir.name,
        fileCount=len(files),
        size=format_file_size(total_size),
        date=import_date.strftime("%b %d, %Y"),
        files=files,
        metadata=RawFolderMetadata(
            importedAt=import_date.strftime("%b %d, %Y %I:%M %p"),
            totalFiles=len(files),
            totalSize=format_file_size(total_size),
            avgSize=format_file_size(int(avg_size)),
            largest=format_file_size(largest),
            smallest=format_file_size(smallest)
        )
    )


def run_ingestion(folder_path: str, label: str, time_interval: float, chunk_duration: float, padding: float):
    """Background task to run data ingestion."""
    from database_management import ingest_sensor_data
    from settings import configs

    # Temporarily update configs
    original_interval = configs.DB_TIME_INTERVAL
    original_chunk = configs.DB_CHUNK_DURATION
    original_padding = configs.DB_PADDING_DURATION

    try:
        configs.DB_TIME_INTERVAL = time_interval
        configs.DB_CHUNK_DURATION = chunk_duration
        configs.DB_PADDING_DURATION = padding

        ingest_sensor_data(folder_path, label)

        # Auto-generate AI metadata after ingestion completes
        print(f"[INFO] Generating AI metadata for label: {label}")
        generate_ai_metadata_for_label(label)

    finally:
        # Restore original configs
        configs.DB_TIME_INTERVAL = original_interval
        configs.DB_CHUNK_DURATION = original_chunk
        configs.DB_PADDING_DURATION = original_padding


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest_data(request: IngestRequest, background_tasks: BackgroundTasks):
    """Trigger data ingestion/processing."""
    folder_path = Path(request.folderPath)

    if not folder_path.exists():
        raise HTTPException(status_code=400, detail=f"Folder path does not exist: {request.folderPath}")

    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.folderPath}")

    # Validate label - comprehensive checks
    label = request.classificationLabel.strip() if request.classificationLabel else ""
    if not label:
        raise HTTPException(status_code=400, detail="Classification label cannot be empty")

    # Check label length (filesystem limits)
    if len(label) > 100:
        raise HTTPException(
            status_code=400,
            detail="Classification label is too long (max 100 characters)"
        )

    # Check for invalid characters that could cause filesystem issues
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
    for char in invalid_chars:
        if char in label:
            raise HTTPException(
                status_code=400,
                detail=f"Classification label contains invalid character: '{char}'"
            )

    # Check if label already exists
    existing_label_dir = DATABASE_DIR / label
    if existing_label_dir.exists():
        raise HTTPException(
            status_code=400,
            detail=f"A dataset with the label '{label}' already exists. Please choose a different name."
        )

    # Run ingestion in background
    background_tasks.add_task(
        run_ingestion,
        str(folder_path),
        label,
        request.timeInterval,
        request.chunkDuration,
        request.padding
    )

    return IngestResponse(
        success=True,
        message=f"Data ingestion started for label '{label}'",
        label=label
    )


@app.post("/api/suggest-label", response_model=SuggestLabelResponse)
async def suggest_label(request: SuggestLabelRequest):
    """Use GPT to suggest a classification label based on folder path."""
    folder_path = request.folderPath
    folder_name = Path(folder_path).name

    def _generate_fallback_label(name: str) -> str:
        """Generate a label using simple rules when AI is not available."""
        label = name
        label = re.sub(r'^split_data_', '', label)
        label = re.sub(r'^data_', '', label)
        label = re.sub(r'[^a-zA-Z0-9_.-]', '_', label)
        label = re.sub(r'_+', '_', label)
        label = label.strip('_').lower()
        return label if label else "dataset"

    def _call_openai():
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """You are a helper that generates classification labels for sensor data folders.
Given a folder path or name, extract a clean, descriptive label suitable for use in machine learning datasets.

Rules:
- Use only lowercase letters, numbers, underscores, and dots
- NO spaces - use underscores instead
- Keep it concise but descriptive
- Extract the key identifying information (material type, test condition, measurement value)
- Examples:
  - "split_data_0.75_crushcore" -> "0.75_crushcore"
  - "OneDrive_1_11-24-2025 copy/disbond_test_1.0" -> "disbond_1.0"
  - "normal_samples_batch2" -> "normal"
  - "impact_damage_severe" -> "impact_severe"

Return ONLY the label, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Generate a classification label for this folder: {folder_path}"
                }
            ],
            temperature=0.3,
            timeout=30.0
        )

        # Safely extract content from response
        if not response.choices or len(response.choices) == 0:
            return None
        content = response.choices[0].message.content
        if not content:
            return None
        return content.strip()

    # Try OpenAI, fall back to simple extraction
    suggested_label = _safe_openai_call(
        _call_openai,
        fallback_value=None,
        error_prefix="Label suggestion"
    )

    if suggested_label:
        # Clean up the label to ensure it matches our format
        suggested_label = re.sub(r'[^a-zA-Z0-9_.-]', '_', suggested_label)
        suggested_label = re.sub(r'_+', '_', suggested_label)  # Remove multiple underscores
        suggested_label = suggested_label.strip('_')  # Remove leading/trailing underscores

        if suggested_label:  # Make sure we still have something after cleanup
            return SuggestLabelResponse(
                success=True,
                label=suggested_label
            )

    # Fallback: extract from folder name using simple rules
    return SuggestLabelResponse(
        success=True,
        label=_generate_fallback_label(folder_name),
        message="Used automatic label extraction"
    )


class SuggestModelNameRequest(BaseModel):
    labels: list[str]
    architecture: str


class SuggestModelNameResponse(BaseModel):
    success: bool
    name: Optional[str] = None
    message: Optional[str] = None


@app.post("/api/suggest-model-name", response_model=SuggestModelNameResponse)
async def suggest_model_name(request: SuggestModelNameRequest):
    """Use GPT to suggest a model name based on labels and architecture."""
    # Get existing model names to avoid duplicates
    existing_names = set()
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                existing_names.add(model_dir.name.lower())

    def _generate_fallback_name() -> str:
        """Generate a model name using simple rules."""
        arch_short = request.architecture.lower()[:6] if request.architecture else "model"
        if request.labels and len(request.labels) > 0:
            # Safely get first label
            label_part = request.labels[0][:10].lower() if request.labels[0] else "data"
            name = f"{arch_short}_{label_part}_model"
        else:
            name = f"{arch_short}_model"

        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name).strip('_')

        # Ensure name is unique
        if name in existing_names:
            counter = 2
            base_name = name
            while f"{base_name}_{counter}" in existing_names:
                counter += 1
            name = f"{base_name}_{counter}"

        return name

    def _call_openai():
        # Include existing names in the prompt so GPT avoids them
        existing_names_str = ", ".join(sorted(existing_names)) if existing_names else "none"

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helper that generates model names for neural network training.
Given a list of classification labels and architecture type, create a concise, descriptive model name.

Rules:
- Use only lowercase letters, numbers, and underscores
- NO spaces - use underscores instead
- Keep it short but descriptive (max 30 chars)
- Include the architecture type abbreviated (cnn, resnet)
- Include key info from the labels
- IMPORTANT: Do NOT use any of these existing names: [{existing_names_str}]
- If your preferred name already exists, append a number like _2, _3, etc.
- Examples:
  - labels: ["crushcore", "disbond"], arch: CNN -> "cnn_crushcore_disbond"
  - labels: ["normal", "impact_severe"], arch: ResNet -> "resnet_impact_classifier"
  - If "cnn_crushcore_disbond" exists -> "cnn_crushcore_disbond_2"

Return ONLY the model name, nothing else."""
                },
                {
                    "role": "user",
                    "content": f"Generate a model name for:\nLabels: {request.labels}\nArchitecture: {request.architecture}"
                }
            ],
            temperature=0.3,
            timeout=30.0
        )

        # Safely extract content
        if not response.choices or len(response.choices) == 0:
            return None
        content = response.choices[0].message.content
        if not content:
            return None
        return content.strip()

    # Try OpenAI first
    suggested_name = _safe_openai_call(
        _call_openai,
        fallback_value=None,
        error_prefix="Model name suggestion"
    )

    if suggested_name:
        # Clean up the name
        suggested_name = re.sub(r'[^a-zA-Z0-9_]', '_', suggested_name)
        suggested_name = re.sub(r'_+', '_', suggested_name)
        suggested_name = suggested_name.strip('_').lower()

        if suggested_name:  # Ensure we still have something
            # Double-check: if name still exists, append a number
            if suggested_name in existing_names:
                counter = 2
                base_name = suggested_name
                while f"{base_name}_{counter}" in existing_names:
                    counter += 1
                suggested_name = f"{base_name}_{counter}"

            return SuggestModelNameResponse(
                success=True,
                name=suggested_name
            )

    # Fallback
    return SuggestModelNameResponse(
        success=True,
        name=_generate_fallback_name(),
        message="Used automatic name generation"
    )


# ============ Training API Models ============

class TrainingRequest(BaseModel):
    model_name: str
    labels: list[str]  # List of label names to train on
    architecture: str = "CNN"  # "CNN" or "ResNet"
    generate_report: bool = True
    use_llm: bool = True


class TrainingStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "preparing", "building", "training", "complete", "error"
    current_step: int
    current_epoch: Optional[int] = None
    total_epochs: Optional[int] = None
    progress_message: str = ""
    error_message: Optional[str] = None
    result: Optional[dict] = None


class ModelInfo(BaseModel):
    id: str
    name: str
    accuracy: str
    loss: str
    date: str
    architecture: str
    status: str
    path: str
    test_accuracy: Optional[str] = None
    training_time: Optional[float] = None  # Training duration in seconds
    report_path: Optional[str] = None


class ReportInfo(BaseModel):
    id: str
    name: str
    size: str
    date: str
    model_name: str
    path: str
    training_time: Optional[float] = None  # Training duration in seconds


# Training job tracking with file-based persistence
TRAINING_JOBS_FILE = Path(__file__).parent / "training_jobs.json"

# Training state persistence folder - stores everything until user clicks "New Run"
TRAINING_PERSISTENCE_DIR = Path(__file__).parent / "training_persistence"
TRAINING_PERSISTENCE_DIR.mkdir(exist_ok=True)

TRAINING_STATE_FILE = TRAINING_PERSISTENCE_DIR / "state.json"
TRAINING_RESULT_FILE = TRAINING_PERSISTENCE_DIR / "result.json"


class TrainingState(BaseModel):
    model_name: str = ""
    selected_labels: list[str] = []
    architecture: str = "CNN"
    last_updated: str = ""
    status: str = "idle"  # idle, training, complete, error
    job_id: str | None = None
    result: dict | None = None  # accuracy, loss, model_path, report_path


def _load_training_state() -> dict:
    """Load saved training state from disk."""
    state = {}

    # Load main state
    if TRAINING_STATE_FILE.exists():
        try:
            with open(TRAINING_STATE_FILE) as f:
                state = json.load(f)
        except Exception:
            state = {}

    # Load result separately (in case it's large)
    if TRAINING_RESULT_FILE.exists():
        try:
            with open(TRAINING_RESULT_FILE) as f:
                result_data = json.load(f)
                state["result"] = result_data.get("result")
                state["status"] = result_data.get("status", state.get("status", "idle"))
                state["job_id"] = result_data.get("job_id", state.get("job_id"))
        except Exception:
            pass

    return state


def _save_training_state(state: dict):
    """Save training state to disk."""
    state["last_updated"] = datetime.now().isoformat()

    # Save result separately
    result_data = {
        "result": state.get("result"),
        "status": state.get("status", "idle"),
        "job_id": state.get("job_id"),
        "last_updated": state["last_updated"]
    }
    with open(TRAINING_RESULT_FILE, "w") as f:
        json.dump(result_data, f, indent=2)

    # Save main state (without result to avoid duplication)
    main_state = {k: v for k, v in state.items() if k != "result"}
    with open(TRAINING_STATE_FILE, "w") as f:
        json.dump(main_state, f, indent=2)


@app.get("/api/training/state", response_model=TrainingState)
async def get_training_state():
    """Get saved training state."""
    state = _load_training_state()
    return TrainingState(**state)


@app.post("/api/training/state")
async def save_training_state_endpoint(state: TrainingState):
    """Save training state for persistence across navigation."""
    _save_training_state(state.model_dump())
    return {"success": True}


@app.delete("/api/training/state")
async def clear_training_state():
    """Clear saved training state - only called when user clicks New Run."""
    if TRAINING_STATE_FILE.exists():
        TRAINING_STATE_FILE.unlink()
    if TRAINING_RESULT_FILE.exists():
        TRAINING_RESULT_FILE.unlink()
    return {"success": True}


def _load_training_jobs() -> dict[str, dict]:
    """Load training jobs from disk (thread-safe)."""
    with _training_jobs_lock:
        if TRAINING_JOBS_FILE.exists():
            try:
                with open(TRAINING_JOBS_FILE) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Could not load training jobs: {e}")
                return {}
        return {}

def _save_training_jobs(jobs: dict[str, dict]):
    """Save training jobs to disk (thread-safe)."""
    with _training_jobs_lock:
        try:
            with open(TRAINING_JOBS_FILE, "w") as f:
                json.dump(jobs, f, indent=2)
        except IOError as e:
            print(f"[ERROR] Could not save training jobs: {e}")

# Track which jobs should be stopped
_stop_requested: dict[str, bool] = {}

training_jobs: dict[str, dict] = _load_training_jobs()


def run_training_job(job_id: str, model_name: str, labels: list[str], architecture: str, generate_report: bool, use_llm: bool):
    """Background task to run training."""
    import tensorflow as tf
    from training import run_training, DataConfig
    from training.config import CNNConfig, ResNetConfig

    def update_job(updates: dict):
        """Update job status and persist to disk (thread-safe)."""
        with _training_jobs_lock:
            if job_id in training_jobs:
                training_jobs[job_id].update(updates)
        _save_training_jobs(training_jobs)

    def is_stop_requested() -> bool:
        """Check if this job should be stopped."""
        return _stop_requested.get(job_id, False)

    def cleanup_gpu():
        """Clean up GPU memory after training."""
        try:
            tf.keras.backend.clear_session()
            # Force garbage collection
            import gc
            gc.collect()
        except Exception as e:
            print(f"[WARNING] GPU cleanup error (non-fatal): {e}")

    # Create epoch progress callback with stop checking
    class EpochProgressCallback(tf.keras.callbacks.Callback):
        """Callback to report epoch progress and check for stop requests."""

        def __init__(self, total_epochs: int, update_fn, stop_check_fn):
            super().__init__()
            self.total_epochs = total_epochs
            self.update_fn = update_fn
            self.stop_check_fn = stop_check_fn

        def on_epoch_begin(self, epoch, logs=None):
            # Check if stop was requested
            if self.stop_check_fn():
                self.model.stop_training = True
                self.update_fn({
                    "status": "error",
                    "error_message": "Training stopped by user",
                    "progress_message": "Training stopped"
                })
                return

            self.update_fn({
                "current_epoch": epoch + 1,
                "total_epochs": self.total_epochs,
                "progress_message": f"Training epoch {epoch + 1}/{self.total_epochs}..."
            })

        def on_epoch_end(self, epoch, logs=None):
            acc = logs.get('accuracy', 0) if logs else 0
            val_acc = logs.get('val_accuracy', 0) if logs else 0
            self.update_fn({
                "current_epoch": epoch + 1,
                "progress_message": f"Epoch {epoch + 1}/{self.total_epochs} - Acc: {acc:.3f}, Val Acc: {val_acc:.3f}"
            })

            # Check for stop request after each epoch
            if self.stop_check_fn():
                self.model.stop_training = True

    try:
        # Update status: preparing
        update_job({
            "status": "preparing",
            "current_step": 1,
            "progress_message": "Preparing data..."
        })

        # Collect all CSV paths from selected labels
        data_paths = []
        for label in labels:
            label_dir = DATABASE_DIR / label
            if label_dir.exists():
                data_paths.append(str(label_dir))

        if not data_paths:
            raise ValueError("No data found for selected labels")

        # Create models directory
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        save_dir = str(MODELS_DIR / model_name)

        # Get total epochs from config based on architecture
        if architecture.lower() == "resnet":
            config = ResNetConfig()
        else:
            config = CNNConfig()
        total_epochs = config.epochs

        # Update job with actual total epochs
        update_job({
            "total_epochs": total_epochs
        })

        # Update status: building
        update_job({
            "status": "building",
            "current_step": 2,
            "progress_message": "Building model..."
        })

        # Create epoch progress callback with stop checking
        epoch_callback = EpochProgressCallback(total_epochs, update_job, is_stop_requested)

        # Update status: training
        update_job({
            "status": "training",
            "current_step": 3,
            "progress_message": "Training model..."
        })

        # Run training with epoch callback
        result = run_training(
            paths=data_paths,
            save_dir=save_dir,
            model_type=architecture.lower(),
            model_name=model_name,
            generate_report=generate_report,
            use_llm=use_llm,
            verbose=True,
            extra_callbacks=[epoch_callback],
        )

        # Update status: complete
        training_result = {
            "accuracy": f"{result.training_result.test_accuracy * 100:.1f}%",
            "loss": f"{result.training_result.test_loss:.4f}",
            "model_path": save_dir,
            "report_path": result.report_path,
        }
        update_job({
            "status": "complete",
            "current_step": 4,
            "progress_message": "Training complete!",
            "result": training_result,
        })

        # Persist training state to disk (survives page refresh until New Run)
        _save_training_state({
            "model_name": model_name,
            "selected_labels": labels,
            "architecture": architecture,
            "status": "complete",
            "job_id": job_id,
            "result": training_result,
        })

        # Save model metadata
        model_metadata = {
            "name": model_name,
            "architecture": architecture,
            "accuracy": result.training_result.test_accuracy,
            "loss": result.training_result.test_loss,
            "labels": labels,
            "created_at": datetime.now().isoformat(),
            "report_path": result.report_path,
            "training_time": result.training_result.training_time,
        }

        model_dir = Path(save_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        with open(model_dir / "model_info.json", "w") as f:
            json.dump(model_metadata, f, indent=2)

    except Exception as e:
        error_msg = str(e)
        # Provide user-friendly error messages
        if "out of memory" in error_msg.lower() or "oom" in error_msg.lower():
            user_msg = "Training failed: Not enough GPU memory. Try using fewer datasets or a smaller model."
        elif "no data found" in error_msg.lower():
            user_msg = "Training failed: No data found for the selected datasets. Please check your data."
        elif "cuda" in error_msg.lower() or "gpu" in error_msg.lower():
            user_msg = "Training failed: GPU error. The system may need to be restarted."
        elif "permission" in error_msg.lower():
            user_msg = "Training failed: Cannot save files. Check disk permissions."
        else:
            user_msg = f"Training failed: {error_msg}"

        update_job({
            "status": "error",
            "error_message": user_msg,
            "progress_message": user_msg
        })
    finally:
        # Always clean up GPU memory and stop tracking
        cleanup_gpu()
        # Remove from stop tracking
        _stop_requested.pop(job_id, None)


@app.post("/api/training/start")
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Start a new training job."""
    import uuid

    # Validate request has labels
    if not request.labels or len(request.labels) == 0:
        raise HTTPException(
            status_code=400,
            detail="Please select at least one dataset to train on"
        )

    # Need at least 2 labels for classification
    if len(request.labels) < 2:
        raise HTTPException(
            status_code=400,
            detail="Please select at least 2 different datasets to train a classifier"
        )

    # Validate model name
    model_name = request.model_name.strip() if request.model_name else ""
    if not model_name:
        raise HTTPException(
            status_code=400,
            detail="Please provide a name for your model"
        )

    # Check model name length
    if len(model_name) > 100:
        raise HTTPException(
            status_code=400,
            detail="Model name is too long (max 100 characters)"
        )

    # Check for invalid characters in model name
    if not re.match(r'^[a-zA-Z0-9_-]+$', model_name):
        raise HTTPException(
            status_code=400,
            detail="Model name can only contain letters, numbers, underscores, and hyphens"
        )

    # Check if model already exists
    if (MODELS_DIR / model_name).exists():
        raise HTTPException(
            status_code=400,
            detail=f"A model named '{model_name}' already exists. Please choose a different name."
        )

    # Validate architecture
    if request.architecture not in ["CNN", "ResNet"]:
        raise HTTPException(
            status_code=400,
            detail="Architecture must be 'CNN' or 'ResNet'"
        )

    # Validate labels exist and have data
    for label in request.labels:
        label_dir = DATABASE_DIR / label
        if not label_dir.exists():
            raise HTTPException(status_code=400, detail=f"Dataset '{label}' not found")

        # Check if label directory has CSV files
        csv_files = list(label_dir.glob("*.csv"))
        if not csv_files:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset '{label}' has no data files. Please add data first."
            )

    # Create job
    job_id = str(uuid.uuid4())[:8]
    with _training_jobs_lock:
        training_jobs[job_id] = {
            "job_id": job_id,
            "model_name": model_name,  # Use validated model_name
            "labels": request.labels,
            "architecture": request.architecture,
            "status": "pending",
            "current_step": 0,
            "current_epoch": None,
            "total_epochs": 50,
            "progress_message": "Initializing...",
            "error_message": None,
            "result": None,
            "created_at": datetime.now().isoformat(),
        }
    _save_training_jobs(training_jobs)

    # Start training in background thread (not FastAPI background task for long-running)
    thread = threading.Thread(
        target=run_training_job,
        args=(job_id, model_name, request.labels, request.architecture, request.generate_report, request.use_llm),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "message": f"Training started for model '{model_name}'"}


@app.get("/api/training/status/{job_id}", response_model=TrainingStatusResponse)
async def get_training_status(job_id: str):
    """Get status of a training job."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

    job = training_jobs[job_id]
    return TrainingStatusResponse(**job)


@app.post("/api/training/stop/{job_id}")
async def stop_training(job_id: str):
    """Stop a training job. The training will stop after the current epoch completes."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

    job_status = training_jobs[job_id].get("status", "")

    # Can only stop jobs that are actually running
    if job_status not in ["pending", "preparing", "building", "training"]:
        return {
            "success": False,
            "message": f"Cannot stop job - it is already {job_status}"
        }

    # Request stop - the training callback will check this flag
    _stop_requested[job_id] = True

    # Update job status
    with _training_jobs_lock:
        training_jobs[job_id]["progress_message"] = "Stop requested - finishing current epoch..."
    _save_training_jobs(training_jobs)

    return {
        "success": True,
        "message": "Stop requested. Training will stop after the current epoch completes."
    }


def _detect_model_architecture(model_dir: Path) -> str:
    """Detect model architecture from files in directory."""
    for f in model_dir.iterdir():
        name = f.name.lower()
        if "resnet" in name:
            return "ResNet"
        elif "cnn" in name:
            return "CNN"
    return "Unknown"


def _generate_model_info(model_dir: Path) -> dict:
    """Generate model_info.json for a model directory that lacks one."""
    # Try to detect architecture from filenames
    architecture = _detect_model_architecture(model_dir)

    # Try to find any keras/h5 model file for creation date
    model_files = list(model_dir.glob("*.keras")) + list(model_dir.glob("*.h5"))
    if model_files:
        created_at = datetime.fromtimestamp(model_files[0].stat().st_mtime)
    else:
        created_at = datetime.now()

    # Find report if exists
    report_files = list(model_dir.glob("*.pdf"))
    report_path = str(report_files[0]) if report_files else None

    info = {
        "name": model_dir.name,
        "architecture": architecture,
        "accuracy": 0.0,
        "loss": 0.0,
        "created_at": created_at.isoformat(),
        "report_path": report_path,
        "auto_generated": True,
    }

    # Save the generated info
    info_path = model_dir / "model_info.json"
    with open(info_path, "w") as f:
        json.dump(info, f, indent=2)

    return info


@app.get("/api/models", response_model=list[ModelInfo])
async def get_models():
    """Get list of all trained models."""
    models = []

    if not MODELS_DIR.exists():
        return models

    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir():
            # Skip hidden directories
            if model_dir.name.startswith('.'):
                continue

            info_path = model_dir / "model_info.json"

            if info_path.exists():
                with open(info_path) as f:
                    info = json.load(f)
            else:
                # Auto-generate model info if missing
                info = _generate_model_info(model_dir)

            test_acc = info.get('test_accuracy', info.get('accuracy', 0))
            training_time = info.get('training_time', 0.0)

            models.append(ModelInfo(
                id=model_dir.name,
                name=info.get("name", model_dir.name),
                accuracy=f"{info.get('accuracy', 0) * 100:.1f}%",
                loss=f"{info.get('loss', 0):.4f}",
                date=datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
                architecture=info.get("architecture", "Unknown"),
                status="Active",
                path=str(model_dir),
                test_accuracy=f"{test_acc * 100:.1f}%",
                training_time=training_time,
                report_path=info.get("report_path"),
            ))

    # Sort by date (newest first)
    models.sort(key=lambda m: m.date, reverse=True)
    return models


@app.get("/api/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """Get details for a specific model."""
    model_dir = MODELS_DIR / model_id

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    info_path = model_dir / "model_info.json"
    if info_path.exists():
        with open(info_path) as f:
            info = json.load(f)
    else:
        # Auto-generate model info if missing
        info = _generate_model_info(model_dir)

    test_acc = info.get('test_accuracy', info.get('accuracy', 0))
    training_time = info.get('training_time', 0.0)

    return ModelInfo(
        id=model_dir.name,
        name=info.get("name", model_dir.name),
        accuracy=f"{info.get('accuracy', 0) * 100:.1f}%",
        loss=f"{info.get('loss', 0):.4f}",
        date=datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d %H:%M:%S"),
        architecture=info.get("architecture", "Unknown"),
        status="Active",
        path=str(model_dir),
        test_accuracy=f"{test_acc * 100:.1f}%",
        training_time=training_time,
        report_path=info.get("report_path"),
    )


class ModelGraphs(BaseModel):
    accuracy: Optional[str] = None  # base64 encoded PNG
    loss: Optional[str] = None
    confusion_matrix: Optional[str] = None


@app.get("/api/models/{model_id}/graphs", response_model=ModelGraphs)
async def get_model_graphs(model_id: str):
    """Get model training graphs as base64 encoded images."""
    import base64

    model_dir = MODELS_DIR / model_id
    graphs_dir = model_dir / "graphs"

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    graphs = ModelGraphs()

    if graphs_dir.exists():
        # Read accuracy graph
        accuracy_path = graphs_dir / "accuracy.png"
        if accuracy_path.exists():
            with open(accuracy_path, "rb") as f:
                graphs.accuracy = base64.b64encode(f.read()).decode("utf-8")

        # Read loss graph
        loss_path = graphs_dir / "loss.png"
        if loss_path.exists():
            with open(loss_path, "rb") as f:
                graphs.loss = base64.b64encode(f.read()).decode("utf-8")

        # Read confusion matrix
        matrix_path = graphs_dir / "confusion_matrix.png"
        if matrix_path.exists():
            with open(matrix_path, "rb") as f:
                graphs.confusion_matrix = base64.b64encode(f.read()).decode("utf-8")

    return graphs


@app.get("/api/models/{model_id}/history")
async def get_model_history(model_id: str):
    """Get training history for interactive charts."""
    model_dir = MODELS_DIR / model_id
    history_path = model_dir / "training_history.json"

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    if not history_path.exists():
        return {"history": None}

    with open(history_path) as f:
        history = json.load(f)

    return {"history": history}


@app.get("/api/models/{model_id}/dependencies")
async def get_model_dependencies_endpoint(model_id: str):
    """
    Preview what will be affected when deleting a model.

    Returns counts of:
    - training_jobs: Number of training job entries that reference this model
    - tests: Number of inference tests that used this model
    - is_current_training_state: Whether this model is the current training state
    """
    from utils.delete_model import get_model_dependencies

    model_dir = MODELS_DIR / model_id

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    dependencies = get_model_dependencies(model_id)

    return {
        "model_id": model_id,
        "dependencies": dependencies
    }


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """
    Delete a model and clean up all related metadata.

    This includes:
    - Model directory and all files
    - Training job entries in training_jobs.json
    - Training state persistence if it references this model
    - Tests are updated to mark the model as deleted (but preserved)
    """
    from utils.delete_model import delete_model_complete, get_model_dependencies

    model_dir = MODELS_DIR / model_id

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    # Perform comprehensive deletion
    results = delete_model_complete(model_id)

    # Build response message
    messages = [f"Model '{model_id}' deleted"]

    if results["reports_archived"] > 0:
        messages.append(f"{results['reports_archived']} report(s) archived")

    if results["training_jobs_cleaned"] > 0:
        messages.append(f"{results['training_jobs_cleaned']} training job(s) removed from history")

    if results["training_state_cleared"]:
        messages.append("Training UI state cleared")

    if results["tests_updated"] > 0:
        messages.append(f"{results['tests_updated']} test(s) updated")

    if results["errors"]:
        return {
            "success": True,
            "message": ". ".join(messages),
            "warnings": results["errors"],
            "details": results
        }

    return {
        "success": True,
        "message": ". ".join(messages),
        "details": results
    }


@app.get("/api/models/{model_id}/weights")
async def download_model_weights(model_id: str):
    """Download the .keras weights file for a model."""
    model_dir = MODELS_DIR / model_id

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    # Look for .keras file first (preferred), then .h5
    keras_files = list(model_dir.glob("*.keras"))
    if keras_files:
        weights_path = keras_files[0]
    else:
        h5_files = list(model_dir.glob("*.h5"))
        if h5_files:
            weights_path = h5_files[0]
        else:
            raise HTTPException(status_code=404, detail="No weights file found for this model")

    return FileResponse(
        weights_path,
        media_type="application/octet-stream",
        filename=weights_path.name
    )


@app.get("/api/reports", response_model=list[ReportInfo])
async def get_reports():
    """Get list of all training reports."""
    reports = []

    # Check models directory for reports
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                # Try to load model info for training_time
                training_time = None
                model_info_path = model_dir / "model_info.json"
                if model_info_path.exists():
                    try:
                        with open(model_info_path) as f:
                            model_info = json.load(f)
                            training_time = model_info.get("training_time")
                    except Exception:
                        pass

                # Look for PDF reports
                for pdf_file in model_dir.glob("*.pdf"):
                    stat = pdf_file.stat()
                    reports.append(ReportInfo(
                        id=pdf_file.stem,
                        name=pdf_file.name,
                        size=format_file_size(stat.st_size),
                        date=datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %H:%M"),
                        model_name=model_dir.name,
                        path=str(pdf_file),
                        training_time=training_time,
                    ))

    # Also include archived reports from deleted models
    reports_archive = BACKEND_DIR / "reports_archive"
    if reports_archive.exists():
        for pdf_file in reports_archive.glob("*.pdf"):
            # Try to load archived report metadata
            metadata_path = pdf_file.with_suffix(".json")
            model_name = "[Archived]"
            if metadata_path.exists():
                try:
                    with open(metadata_path) as f:
                        meta = json.load(f)
                        model_name = f"{meta.get('original_model', 'Unknown')} [Archived]"
                except Exception:
                    pass

            stat = pdf_file.stat()
            reports.append(ReportInfo(
                id=pdf_file.stem,
                name=pdf_file.name,
                size=format_file_size(stat.st_size),
                date=datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y %H:%M"),
                model_name=model_name,
                path=str(pdf_file),
                training_time=None,
            ))

    # Sort by date (newest first)
    reports.sort(key=lambda r: r.date, reverse=True)
    return reports


@app.delete("/api/reports/{report_id}")
async def delete_report(report_id: str):
    """Delete a specific report PDF."""
    # Search in models directory first
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                for pdf_file in model_dir.glob("*.pdf"):
                    if pdf_file.stem == report_id:
                        pdf_file.unlink()
                        return {"success": True, "message": f"Report {report_id} deleted"}

    # Search in reports archive
    reports_archive = BACKEND_DIR / "reports_archive"
    if reports_archive.exists():
        for pdf_file in reports_archive.glob("*.pdf"):
            if pdf_file.stem == report_id:
                pdf_file.unlink()
                # Also remove metadata if exists
                metadata_path = pdf_file.with_suffix(".json")
                if metadata_path.exists():
                    metadata_path.unlink()
                return {"success": True, "message": f"Archived report {report_id} deleted"}

    raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")


@app.get("/api/training/report/view")
async def view_report(path: str):
    """View a PDF report."""
    report_path = Path(path)

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(report_path, media_type="application/pdf")


@app.get("/api/training/report/download")
async def download_report(path: str):
    """Download a PDF report."""
    report_path = Path(path)

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=report_path.name
    )


@app.get("/api/reports/{model_id}/{filename}")
async def get_report_by_model(model_id: str, filename: str):
    """Get a specific report PDF for a model."""
    model_dir = MODELS_DIR / model_id
    report_path = model_dir / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    # Validate it's a PDF
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files can be retrieved")

    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=filename
    )


@app.get("/api/reports/export-all")
async def export_all_reports():
    """Download all reports as a ZIP file."""
    # Collect all PDF reports
    pdf_files = []
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                for pdf_file in model_dir.glob("*.pdf"):
                    pdf_files.append(pdf_file)

    if not pdf_files:
        raise HTTPException(status_code=404, detail="No reports found to export")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for pdf_path in pdf_files:
            # Use model_name/report.pdf structure in ZIP
            arcname = f"{pdf_path.parent.name}/{pdf_path.name}"
            zip_file.write(pdf_path, arcname)

    zip_buffer.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"all_reports_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ Testing/Inference API ============

# Testing database and inference module imports (lazy loaded)
_test_database = None


def get_test_database():
    """Get or create the test database instance."""
    global _test_database
    if _test_database is None:
        from testing import TestDatabase, TestDatabaseConfig
        config = TestDatabaseConfig(db_root=Path(__file__).parent / "test_database")
        _test_database = TestDatabase(config)
    return _test_database


class TestSummary(BaseModel):
    test_id: str
    timestamp: str
    csv_filename: str
    model_name: str
    num_chunks: int
    majority_class: str
    majority_confidence: float
    tags: list[str] = []


class TestDetail(BaseModel):
    test_id: str
    timestamp: str
    original_csv_path: str
    stored_csv_path: str
    model_path: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    processing_metadata: Optional[dict] = None
    num_chunks: int = 0
    predictions: Optional[list[str]] = None
    probabilities: Optional[list[list[float]]] = None
    class_ids: Optional[list[int]] = None
    majority_class: Optional[str] = None
    majority_count: Optional[int] = None
    majority_percentage: Optional[float] = None
    processed_chunks_dir: Optional[str] = None
    auto_detect_csv: bool = True
    csv_structure: Optional[dict] = None
    notes: Optional[str] = None
    tags: list[str] = []


class TestStatsResponse(BaseModel):
    total_tests: int
    total_size_mb: float
    unique_models: int
    unique_tags: int
    models: list[str]
    tags: list[str]


class InferenceRequest(BaseModel):
    csv_path: str
    model_id: str
    notes: Optional[str] = None
    tags: Optional[list[str]] = None
    log_to_database: bool = True


class InferenceResponse(BaseModel):
    success: bool
    test_id: Optional[str] = None
    predictions: list[str] = []
    probabilities: list[list[float]] = []
    majority_class: Optional[str] = None
    majority_confidence: Optional[float] = None
    num_chunks: int = 0
    error: Optional[str] = None


@app.get("/api/tests", response_model=list[TestSummary])
async def list_tests(
    limit: Optional[int] = None,
    model_name: Optional[str] = None,
    tags: Optional[str] = None
):
    """Get list of all tests with optional filtering."""
    db = get_test_database()

    # Parse tags from comma-separated string
    tag_list = tags.split(",") if tags else None

    tests = db.list_tests(limit=limit, model_name=model_name, tags=tag_list)

    result = []
    for t in tests:
        # Load full test metadata to get probabilities
        avg_confidence = 0.0
        try:
            full_test = db.get_test(t["test_id"])
            probabilities = full_test.probabilities or []
            if probabilities and len(probabilities) > 0:
                # Get the max probability for each chunk and average them
                max_probs = [max(probs) if probs else 0 for probs in probabilities]
                avg_confidence = sum(max_probs) / len(max_probs) * 100  # Convert to percentage
        except Exception:
            # Fall back to majority_confidence if loading fails
            avg_confidence = t.get("majority_confidence", 0.0) * 100

        result.append(TestSummary(
            test_id=t["test_id"],
            timestamp=t["timestamp"],
            csv_filename=t.get("csv_filename", ""),
            model_name=t.get("model_name", ""),
            num_chunks=t.get("num_chunks", 0),
            majority_class=t.get("majority_class", ""),
            majority_confidence=avg_confidence,
            tags=t.get("tags", [])
        ))

    return result


@app.get("/api/tests/stats", response_model=TestStatsResponse)
async def get_test_stats():
    """Get test database statistics."""
    db = get_test_database()
    stats = db.get_stats()

    return TestStatsResponse(
        total_tests=stats["total_tests"],
        total_size_mb=stats["total_size_mb"],
        unique_models=stats["unique_models"],
        unique_tags=stats["unique_tags"],
        models=stats["models"],
        tags=stats["tags"]
    )


@app.get("/api/tests/{test_id}", response_model=TestDetail)
async def get_test_detail(test_id: str):
    """Get detailed information about a specific test."""
    db = get_test_database()

    try:
        metadata = db.get_test(test_id)
        return TestDetail(
            test_id=metadata.test_id,
            timestamp=metadata.timestamp,
            original_csv_path=metadata.original_csv_path,
            stored_csv_path=metadata.stored_csv_path,
            model_path=metadata.model_path,
            model_name=metadata.model_name,
            model_version=metadata.model_version,
            processing_metadata=metadata.processing_metadata,
            num_chunks=metadata.num_chunks,
            predictions=metadata.predictions,
            probabilities=metadata.probabilities,
            class_ids=metadata.class_ids,
            majority_class=metadata.majority_class,
            majority_count=metadata.majority_count,
            majority_percentage=metadata.majority_percentage,
            processed_chunks_dir=metadata.processed_chunks_dir,
            auto_detect_csv=metadata.auto_detect_csv,
            csv_structure=metadata.csv_structure,
            notes=metadata.notes,
            tags=metadata.tags or []
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/tests/{test_id}/csv")
async def download_test_csv(test_id: str):
    """Download the raw CSV file for a test."""
    db = get_test_database()

    try:
        csv_path = db.get_csv_path(test_id)
        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="CSV file not found")

        return FileResponse(
            path=csv_path,
            media_type="text/csv",
            filename=csv_path.name
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/tests/{test_id}/chunk/{chunk_idx}")
async def get_test_chunk(test_id: str, chunk_idx: int):
    """Get processed chunk data for a test."""
    db = get_test_database()

    try:
        chunk_data = db.load_chunk(test_id, chunk_idx)
        return {
            "test_id": test_id,
            "chunk_idx": chunk_idx,
            "data": chunk_data.tolist(),
            "shape": list(chunk_data.shape)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/tests/{test_id}/raw-data")
async def get_test_raw_data(test_id: str, max_points: int = 1000):
    """Get raw CSV data for visualization."""
    db = get_test_database()

    try:
        metadata = db.get_test(test_id)
        csv_path = db.get_csv_path(test_id)

        if not csv_path.exists():
            raise HTTPException(status_code=404, detail="CSV file not found")

        # Try reading with different skip_rows values to handle label headers
        df = None
        skip_rows = 0
        for skip in [0, 1, 2]:
            try:
                temp_df = pd.read_csv(csv_path, skiprows=skip)
                # Check if we have at least 2 columns and numeric data
                if len(temp_df.columns) >= 2:
                    # Check if any column is numeric
                    has_numeric = any(pd.api.types.is_numeric_dtype(temp_df[col]) for col in temp_df.columns)
                    if has_numeric:
                        df = temp_df
                        skip_rows = skip
                        break
            except Exception:
                continue

        if df is None:
            raise HTTPException(status_code=400, detail="Could not parse CSV file")

        # Try to detect time and value columns
        time_col = None
        value_col = None

        # Common time column names
        for col in df.columns:
            col_lower = str(col).lower()
            if any(t in col_lower for t in ['time', 'timestamp', 'seconds']):
                time_col = col
                break

        # If no time column found by name, use first numeric column as time
        if time_col is None:
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    time_col = col
                    break

        # If still no time column, use index
        if time_col is None:
            df['_time'] = range(len(df))
            time_col = '_time'

        # Use first numeric column that isn't time as value
        for col in df.columns:
            if col != time_col and pd.api.types.is_numeric_dtype(df[col]):
                value_col = col
                break

        if value_col is None:
            raise HTTPException(status_code=400, detail="No numeric value column found")

        # Downsample if needed
        step = max(1, len(df) // max_points)
        df_sampled = df.iloc[::step]

        return {
            "test_id": test_id,
            "time": df_sampled[time_col].tolist(),
            "values": df_sampled[value_col].tolist(),
            "time_column": time_col if time_col != '_time' else 'index',
            "value_column": value_col,
            "total_points": len(df),
            "sampled_points": len(df_sampled)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/tests/{test_id}")
async def delete_test(test_id: str):
    """Delete a test and all its associated data."""
    db = get_test_database()

    try:
        db.delete_test(test_id)
        return {"success": True, "message": f"Test {test_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class NotesUpdate(BaseModel):
    notes: str


@app.put("/api/tests/{test_id}/notes")
async def update_test_notes(test_id: str, update: NotesUpdate):
    """Update notes for a test."""
    db = get_test_database()

    try:
        test = db.get_test(test_id)
        if not test:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")

        # Update the notes in the database
        db.update_test_notes(test_id, update.notes)
        return {"success": True, "message": "Notes updated"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/tests/{test_id}/generate-notes")
async def generate_test_notes(test_id: str):
    """Generate AI notes for a test based on its results."""
    db = get_test_database()

    try:
        test = db.get_test(test_id)
        if not test:
            raise HTTPException(status_code=404, detail=f"Test {test_id} not found")

        # Build context for AI
        predictions = test.get("predictions", [])
        probabilities = test.get("probabilities", [])
        majority_class = test.get("majority_class", "Unknown")
        majority_percentage = test.get("majority_percentage", 0)
        num_chunks = test.get("num_chunks", 0)
        model_name = test.get("model_name", "Unknown")
        csv_filename = Path(test.get("original_csv_path", "unknown.csv")).name

        # Calculate average confidence
        avg_confidence = 0
        if probabilities:
            confidences = [max(p) * 100 for p in probabilities if p]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)

        # Build the prompt
        prompt = f"""Generate brief, professional test notes for this sensor data analysis test:

File: {csv_filename}
Model Used: {model_name}
Total Chunks Analyzed: {num_chunks}
Predicted Classification: {majority_class}
Classification Confidence: {majority_percentage:.1f}%
Average Chunk Confidence: {avg_confidence:.1f}%
Prediction Distribution: {', '.join(predictions[:10])}{'...' if len(predictions) > 10 else ''}

Please generate concise technical notes (2-4 sentences) summarizing:
1. The test results and confidence levels
2. Any notable patterns or concerns
3. A brief assessment of the classification reliability

Keep the notes factual and professional."""

        # Call OpenAI using the global client
        if not openai_client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a technical analyst generating brief test notes for sensor data analysis results. Be concise and factual."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
        )

        generated_notes = response.choices[0].message.content.strip()
        return {"success": True, "notes": generated_notes}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate notes: {str(e)}")


@app.post("/api/tests/inference", response_model=InferenceResponse)
async def run_inference(request: InferenceRequest):
    """Run inference on a CSV file using a trained model."""
    from testing import predict_from_csv

    csv_path = Path(request.csv_path)

    # Find the serving model - it's named {model_id}_serving
    model_dir = MODELS_DIR / request.model_id
    serving_model_path = model_dir / f"{request.model_id}_serving"

    # Fallback to check other common naming patterns
    if not serving_model_path.exists():
        # Try looking for any directory ending with _serving
        for item in model_dir.iterdir() if model_dir.exists() else []:
            if item.is_dir() and item.name.endswith("_serving"):
                serving_model_path = item
                break

    if not csv_path.exists():
        raise HTTPException(status_code=400, detail=f"CSV file not found: {request.csv_path}")

    if not serving_model_path.exists():
        raise HTTPException(status_code=400, detail=f"Serving model not found for: {request.model_id}. Expected at {serving_model_path}")

    try:
        # Get model info
        model_info_path = MODELS_DIR / request.model_id / "model_info.json"
        model_name = request.model_id
        if model_info_path.exists():
            with open(model_info_path) as f:
                info = json.load(f)
                model_name = info.get("name", request.model_id)

        result = predict_from_csv(
            csv_path=str(csv_path),
            model_path=str(serving_model_path),
            auto_detect=True,
            verbose=False,
            log_to_database=request.log_to_database,
            model_name=model_name,
            notes=request.notes,
            tags=request.tags
        )

        majority_class, _, majority_confidence = result.get_majority_prediction()

        # Get test_id from database if logged
        test_id = None
        if request.log_to_database:
            db = get_test_database()
            tests = db.list_tests(limit=1)
            if tests:
                test_id = tests[0]["test_id"]

        return InferenceResponse(
            success=True,
            test_id=test_id,
            predictions=result.class_names,
            probabilities=result.probabilities.tolist(),
            majority_class=majority_class,
            majority_confidence=majority_confidence,
            num_chunks=len(result.class_names)
        )

    except Exception as e:
        return InferenceResponse(
            success=False,
            error=str(e)
        )


class FileUploadResponse(BaseModel):
    success: bool
    file_path: Optional[str] = None
    filename: Optional[str] = None
    size_kb: Optional[float] = None
    error: Optional[str] = None


@app.post("/api/tests/upload", response_model=FileUploadResponse)
async def upload_test_file(file: UploadFile = File(...)):
    """Upload a CSV file for testing."""
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Create uploads directory
    uploads_dir = Path(__file__).parent / "test_uploads"
    uploads_dir.mkdir(exist_ok=True)

    # Save file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = uploads_dir / safe_filename

    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        return FileUploadResponse(
            success=True,
            file_path=str(file_path),
            filename=file.filename,
            size_kb=len(content) / 1024
        )
    except Exception as e:
        return FileUploadResponse(
            success=False,
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
