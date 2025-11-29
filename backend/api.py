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

from settings.constants import DATABASE_DIR, RAW_DATABASE_DIR, MODELS_DIR, REPORTS_DIR, METADATA_FILENAME, OPENAI_MODEL

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
    from openai import OpenAI

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
        client = OpenAI()

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
    from openai import OpenAI

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

    client = OpenAI()

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
    from openai import OpenAI

    folder_path = request.folderPath
    folder_name = Path(folder_path).name

    try:
        client = OpenAI()

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


# In-memory training job tracking
training_jobs: dict[str, dict] = {}


def run_training_job(job_id: str, model_name: str, labels: list[str], architecture: str, generate_report: bool, use_llm: bool):
    """Background task to run training."""
    import threading
    from training import run_training, DataConfig

    try:
        # Update status: preparing
        training_jobs[job_id]["status"] = "preparing"
        training_jobs[job_id]["current_step"] = 1
        training_jobs[job_id]["progress_message"] = "Preparing data..."

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

        # Update status: building
        training_jobs[job_id]["status"] = "building"
        training_jobs[job_id]["current_step"] = 2
        training_jobs[job_id]["progress_message"] = "Building model..."

        # Update status: training
        training_jobs[job_id]["status"] = "training"
        training_jobs[job_id]["current_step"] = 3
        training_jobs[job_id]["progress_message"] = "Training model..."

        # Run training
        result = run_training(
            paths=data_paths,
            save_dir=save_dir,
            model_type=architecture.lower(),
            model_name=model_name,
            generate_report=generate_report,
            use_llm=use_llm,
            verbose=True,
        )

        # Update status: complete
        training_jobs[job_id]["status"] = "complete"
        training_jobs[job_id]["current_step"] = 4
        training_jobs[job_id]["progress_message"] = "Training complete!"
        training_jobs[job_id]["result"] = {
            "accuracy": f"{result.training_result.test_accuracy * 100:.1f}%",
            "loss": f"{result.training_result.test_loss:.4f}",
            "model_path": save_dir,
            "report_path": result.report_path,
        }

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
        training_jobs[job_id]["status"] = "error"
        training_jobs[job_id]["error_message"] = str(e)
        training_jobs[job_id]["progress_message"] = f"Error: {str(e)}"


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
        "status": "pending",
        "current_step": 0,
        "current_epoch": None,
        "total_epochs": 50,
        "progress_message": "Initializing...",
        "error_message": None,
        "result": None,
    }

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


@app.get("/api/models", response_model=list[ModelInfo])
async def get_models():
    """Get list of all trained models."""
    models = []

    if not MODELS_DIR.exists():
        return models

    for model_dir in MODELS_DIR.iterdir():
        if model_dir.is_dir():
            info_path = model_dir / "model_info.json"
            if info_path.exists():
                with open(info_path) as f:
                    info = json.load(f)

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
    if not info_path.exists():
        raise HTTPException(status_code=404, detail=f"Model info not found for '{model_id}'")

    with open(info_path) as f:
        info = json.load(f)

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
