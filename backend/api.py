"""
FastAPI server for the Damage Lab sensor data application.
Provides REST API endpoints for the React frontend.
"""

import json
import os
import zipfile
import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

from settings.constants import DATABASE_DIR, RAW_DATABASE_DIR, MODELS_DIR, REPORTS_DIR, METADATA_FILENAME, OPENAI_MODEL

# Load environment variables
load_dotenv()

# Initialize OpenAI client once
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI(
    title="Damage Lab API",
    description="API for sensor data visualization and management",
    version="1.0.0"
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5001", "http://localhost:5173", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

        # Save AI metadata back to the metadata.json file
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


class DirectoryItem(BaseModel):
    name: str
    path: str
    isDirectory: bool


@app.get("/api/browse", response_model=list[DirectoryItem])
async def browse_directory(path: str = None):
    """Browse directories on the server for folder selection."""
    # Default to home directory if no path provided
    if not path:
        path = str(Path.home())

    target_path = Path(path)

    if not target_path.exists():
        raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    items = []

    # Add parent directory option (unless at root)
    if target_path.parent != target_path:
        items.append(DirectoryItem(
            name="..",
            path=str(target_path.parent),
            isDirectory=True
        ))

    try:
        for item in sorted(target_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files/folders
            if item.name.startswith('.'):
                continue
            items.append(DirectoryItem(
                name=item.name,
                path=str(item),
                isDirectory=item.is_dir()
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"Permission denied: {path}")

    return items


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

        # Save AI metadata back to the metadata.json file
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

        # Get column names (should be Time(s) and Current (pA) or similar)
        time_col = df.columns[0]
        value_col = df.columns[1]  # This will be like "Current (pA)"

        data_points = []
        for _, row in df.iterrows():
            data_points.append(DataPoint(
                time=float(row[time_col]),
                value=float(row[value_col])
            ))

        return FileDataResponse(
            data=data_points,
            yAxisLabel=value_col  # Return the actual column header
        )
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

    # Validate label
    label = request.classificationLabel.strip()
    if not label:
        raise HTTPException(status_code=400, detail="Classification label cannot be empty")

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
    import re

    folder_path = request.folderPath
    folder_name = Path(folder_path).name

    try:
        client = openai_client

        response = client.chat.completions.create(
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
            temperature=0.3
        )

        suggested_label = response.choices[0].message.content.strip()
        # Clean up the label to ensure it matches our format
        suggested_label = re.sub(r'[^a-zA-Z0-9_.-]', '_', suggested_label)
        suggested_label = re.sub(r'_+', '_', suggested_label)  # Remove multiple underscores
        suggested_label = suggested_label.strip('_')  # Remove leading/trailing underscores

        return SuggestLabelResponse(
            success=True,
            label=suggested_label
        )

    except Exception as e:
        # Fallback: extract from folder name using simple rules
        # Remove common prefixes like "split_data_"
        label = folder_name
        label = re.sub(r'^split_data_', '', label)
        label = re.sub(r'^data_', '', label)
        label = re.sub(r'[^a-zA-Z0-9_.-]', '_', label)
        label = re.sub(r'_+', '_', label)
        label = label.strip('_').lower()

        return SuggestLabelResponse(
            success=True,
            label=label if label else "dataset",
            message=f"Used fallback extraction: {str(e)}"
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
    import re

    # Get existing model names to avoid duplicates
    existing_names = set()
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir() and not model_dir.name.startswith('.'):
                existing_names.add(model_dir.name.lower())

    try:
        client = openai_client

        # Include existing names in the prompt so GPT avoids them
        existing_names_str = ", ".join(sorted(existing_names)) if existing_names else "none"

        response = client.chat.completions.create(
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
            temperature=0.3
        )

        suggested_name = response.choices[0].message.content.strip()
        # Clean up the name
        suggested_name = re.sub(r'[^a-zA-Z0-9_]', '_', suggested_name)
        suggested_name = re.sub(r'_+', '_', suggested_name)
        suggested_name = suggested_name.strip('_').lower()

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

    except Exception as e:
        # Fallback: generate simple name
        arch_short = request.architecture.lower()[:6]
        if request.labels:
            label_part = request.labels[0][:10].lower()
            name = f"{arch_short}_{label_part}_model"
        else:
            name = f"{arch_short}_model"

        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # Ensure fallback name is also unique
        if name in existing_names:
            counter = 2
            base_name = name
            while f"{base_name}_{counter}" in existing_names:
                counter += 1
            name = f"{base_name}_{counter}"

        return SuggestModelNameResponse(
            success=True,
            name=name,
            message=f"Used fallback: {str(e)}"
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
    report_path: Optional[str] = None


class ReportInfo(BaseModel):
    id: str
    name: str
    size: str
    date: str
    model_name: str
    path: str


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
    """Load training jobs from disk."""
    if TRAINING_JOBS_FILE.exists():
        try:
            with open(TRAINING_JOBS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_training_jobs(jobs: dict[str, dict]):
    """Save training jobs to disk."""
    with open(TRAINING_JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

training_jobs: dict[str, dict] = _load_training_jobs()


def run_training_job(job_id: str, model_name: str, labels: list[str], architecture: str, generate_report: bool, use_llm: bool):
    """Background task to run training."""
    import threading
    import tensorflow as tf
    from training import run_training, DataConfig
    from training.config import CNNConfig, ResNetConfig

    def update_job(updates: dict):
        """Update job status and persist to disk."""
        training_jobs[job_id].update(updates)
        _save_training_jobs(training_jobs)

    # Create epoch progress callback
    class EpochProgressCallback(tf.keras.callbacks.Callback):
        """Callback to report epoch progress to the API."""

        def __init__(self, total_epochs: int, update_fn):
            super().__init__()
            self.total_epochs = total_epochs
            self.update_fn = update_fn

        def on_epoch_begin(self, epoch, logs=None):
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

        # Create epoch progress callback
        epoch_callback = EpochProgressCallback(total_epochs, update_job)

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
        }

        model_dir = Path(save_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        with open(model_dir / "model_info.json", "w") as f:
            json.dump(model_metadata, f, indent=2)

    except Exception as e:
        update_job({
            "status": "error",
            "error_message": str(e),
            "progress_message": f"Error: {str(e)}"
        })


@app.post("/api/training/start")
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Start a new training job."""
    import uuid
    import threading

    # Validate labels exist
    for label in request.labels:
        label_dir = DATABASE_DIR / label
        if not label_dir.exists():
            raise HTTPException(status_code=400, detail=f"Label '{label}' not found")

    # Create job
    job_id = str(uuid.uuid4())[:8]
    training_jobs[job_id] = {
        "job_id": job_id,
        "model_name": request.model_name,
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
        args=(job_id, request.model_name, request.labels, request.architecture, request.generate_report, request.use_llm),
        daemon=True
    )
    thread.start()

    return {"job_id": job_id, "message": f"Training started for model '{request.model_name}'"}


@app.get("/api/training/status/{job_id}", response_model=TrainingStatusResponse)
async def get_training_status(job_id: str):
    """Get status of a training job."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

    job = training_jobs[job_id]
    return TrainingStatusResponse(**job)


@app.post("/api/training/stop/{job_id}")
async def stop_training(job_id: str):
    """Stop a training job (if possible)."""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail=f"Training job '{job_id}' not found")

    # Mark as stopped (actual interruption requires more complex handling)
    training_jobs[job_id]["status"] = "error"
    training_jobs[job_id]["error_message"] = "Training stopped by user"

    return {"message": "Training stop requested"}


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

            models.append(ModelInfo(
                id=model_dir.name,
                name=info.get("name", model_dir.name),
                accuracy=f"{info.get('accuracy', 0) * 100:.1f}%",
                loss=f"{info.get('loss', 0):.4f}",
                date=datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d"),
                architecture=info.get("architecture", "Unknown"),
                status="Active",
                path=str(model_dir),
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

    return ModelInfo(
        id=model_dir.name,
        name=info.get("name", model_dir.name),
        accuracy=f"{info.get('accuracy', 0) * 100:.1f}%",
        loss=f"{info.get('loss', 0):.4f}",
        date=datetime.fromisoformat(info.get("created_at", datetime.now().isoformat())).strftime("%Y-%m-%d"),
        architecture=info.get("architecture", "Unknown"),
        status="Active",
        path=str(model_dir),
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


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """Delete a model."""
    import shutil

    model_dir = MODELS_DIR / model_id

    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    shutil.rmtree(model_dir)

    return {"success": True, "message": f"Model '{model_id}' deleted"}


@app.get("/api/reports", response_model=list[ReportInfo])
async def get_reports():
    """Get list of all training reports."""
    reports = []

    # Check models directory for reports
    if MODELS_DIR.exists():
        for model_dir in MODELS_DIR.iterdir():
            if model_dir.is_dir():
                # Look for PDF reports
                for pdf_file in model_dir.glob("*.pdf"):
                    stat = pdf_file.stat()
                    reports.append(ReportInfo(
                        id=pdf_file.stem,
                        name=pdf_file.name,
                        size=format_file_size(stat.st_size),
                        date=datetime.fromtimestamp(stat.st_mtime).strftime("%b %d, %Y"),
                        model_name=model_dir.name,
                        path=str(pdf_file),
                    ))

    # Sort by date (newest first)
    reports.sort(key=lambda r: r.date, reverse=True)
    return reports


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
