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

from settings.constants import DATABASE_DIR, RAW_DATABASE_DIR, METADATA_FILENAME

app = FastAPI(
    title="Damage Lab API",
    description="API for sensor data visualization and management",
    version="1.0.0"
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5173", "http://127.0.0.1:5000"],
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
        )
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
    original_interval = configs.TIME_INTERVAL
    original_chunk = configs.CHUNK_DURATION
    original_padding = configs.PADDING_DURATION

    try:
        configs.TIME_INTERVAL = time_interval
        configs.CHUNK_DURATION = chunk_duration
        configs.PADDING_DURATION = padding

        ingest_sensor_data(folder_path, label)
    finally:
        # Restore original configs
        configs.TIME_INTERVAL = original_interval
        configs.CHUNK_DURATION = original_chunk
        configs.PADDING_DURATION = original_padding


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
            model="gpt-4.1-nano",
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
            max_tokens=50,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
