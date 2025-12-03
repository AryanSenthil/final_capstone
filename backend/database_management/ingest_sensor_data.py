"""
Sensor Data Ingestion Pipeline

Processes raw sensor CSV files into standardized chunks for database storage.
Features:
- Copies raw data to raw_database/ (preserving folder structure)
- Processes and chunks data into database/
- Generates metadata.json for both raw and processed data
- Auto-detects CSV structure using GPT-5.1
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import interp1d
from typing import Union, Optional
import shutil

from .constants import (
    DATABASE_DIR, RAW_DATABASE_DIR,
    CSV_FILE_PATTERN, METADATA_FILENAME,
    CHUNK_FILENAME_TEMPLATE, CHUNK_COUNTER_START,
    MIN_DATA_POINTS,
    LOG_FORMAT_OK, LOG_FORMAT_SKIP, LOG_FORMAT_ERROR
)

from .configs import (
    TIME_INTERVAL, CHUNK_DURATION, PADDING_DURATION,
    INTERPOLATION_KIND, INTERPOLATION_BOUNDS_ERROR, INTERPOLATION_FILL_VALUE,
    AUTO_DETECT_ENABLED, RECURSIVE_SEARCH,
    COPY_RAW_DATA, GENERATE_METADATA, APPEND_MODE
)

from .utils import (
    detect_csv_structure,
    generate_database_metadata,
    generate_raw_database_metadata,
    save_metadata
)


def ingest_sensor_data(
    import_folder_path: Union[str, Path],
    classification_label: str,
    auto_detect: Optional[bool] = None,
    time_interval: Optional[float] = None,
    chunk_duration: Optional[float] = None,
    padding_duration: Optional[float] = None
) -> None:
    """
    Ingest raw sensor data: copy to raw_database/ and process into database/.
    
    This function:
    1. Copies the entire import folder (with structure) to raw_database/
    2. Processes CSV files into interpolated chunks in database/{label}/
    3. Generates metadata.json in both locations
    
    Parameters
    ----------
    import_folder_path : Union[str, Path]
        Path to folder containing raw CSV files (can have subfolders)
        Example: "../../imports/cnn_data/" or "../../imports/test_run_nov_28/"
    classification_label : str
        Label for this dataset (e.g., "normal", "impact", "delamination")
        Creates database/{label}/ folder
    auto_detect : Optional[bool]
        Use GPT-5.1 to detect CSV structure. If None, uses config default.
    time_interval : Optional[float]
        Interpolation time spacing in seconds. If None, uses config default.
    chunk_duration : Optional[float]
        Duration of each chunk in seconds. If None, uses config default.
    padding_duration : Optional[float]
        Zero-padding on each side in seconds. If None, uses config default.
    
    Examples
    --------
    >>> ingest_sensor_data(
    ...     import_folder_path="../../imports/cnn_folder",
    ...     classification_label="normal"
    ... )
    
    >>> ingest_sensor_data(
    ...     import_folder_path="../../imports/impact_test",
    ...     classification_label="impact",
    ...     time_interval=0.05,  # Override config
    ...     chunk_duration=10.0
    ... )
    """
    # Use config defaults if not specified
    if auto_detect is None:
        auto_detect = AUTO_DETECT_ENABLED
    if time_interval is None:
        time_interval = TIME_INTERVAL
    if chunk_duration is None:
        chunk_duration = CHUNK_DURATION
    if padding_duration is None:
        padding_duration = PADDING_DURATION
    
    # Convert to Path
    import_folder = Path(import_folder_path)
    
    if not import_folder.exists():
        raise FileNotFoundError(f"Import folder not found: {import_folder}")
    
    # Setup directories
    database_label_dir = DATABASE_DIR / classification_label
    raw_database_import_dir = RAW_DATABASE_DIR / import_folder.name

    database_label_dir.mkdir(parents=True, exist_ok=True)

    # Check if source folder is ALREADY in raw_database (uploaded via web)
    # In this case, skip the copy step to avoid duplicates
    source_is_in_raw_db = str(import_folder.resolve()).startswith(str(RAW_DATABASE_DIR.resolve()))

    print("="*70)
    print(f"SENSOR DATA INGESTION PIPELINE")
    print("="*70)
    print(f"Import folder: {import_folder}")
    print(f"Classification: {classification_label}")
    if not source_is_in_raw_db:
        print(f"Output (raw): {raw_database_import_dir}")
    else:
        print(f"Source already in raw_database (skipping copy)")
        raw_database_import_dir = import_folder  # Use existing folder
    print(f"Output (processed): {database_label_dir}")
    print("="*70 + "\n")

    # Step 1: Copy raw data to raw_database/ (SKIP if already there)
    if COPY_RAW_DATA and not source_is_in_raw_db:
        print("[STEP 1] Copying raw data to raw_database/...")
        # Handle duplicate folder names like folder, folder(1), folder(2), etc.
        if raw_database_import_dir.exists():
            base_name = import_folder.name
            counter = 1
            while raw_database_import_dir.exists():
                new_name = f"{base_name}({counter})"
                raw_database_import_dir = RAW_DATABASE_DIR / new_name
                counter += 1
            print(f"  Folder already exists, saving as: {raw_database_import_dir.name}")
        shutil.copytree(import_folder, raw_database_import_dir)
        print(f"[OK] Copied to: {raw_database_import_dir}\n")
    elif source_is_in_raw_db:
        print("[STEP 1] Source already in raw_database - skipping copy\n")
    
    # Get all CSV files
    if RECURSIVE_SEARCH:
        csv_files = list(import_folder.rglob(CSV_FILE_PATTERN))
    else:
        csv_files = list(import_folder.glob(CSV_FILE_PATTERN))
    
    if not csv_files:
        print(f"No CSV files found in {import_folder}")
        return
    
    print(f"Found {len(csv_files)} CSV files to process\n")
    
    # Get subfolder structure for metadata
    subfolders = list(set([str(f.parent.relative_to(import_folder)) 
                          for f in csv_files if f.parent != import_folder]))
    
    # Step 2: Auto-detect CSV structure
    if auto_detect:
        print("[STEP 2] Auto-detecting CSV structure with GPT-5.1...")
        print("="*70)
        try:
            structure = detect_csv_structure(csv_files[0])
            time_column = structure["time_column"]
            values_column = structure["values_column"]
            values_label = structure["values_label"]
            skip_rows = structure["skip_rows"]
            
            print(f"[OK] Detected structure:")
            print(f"  - Skip rows: {skip_rows}")
            print(f"  - Time column: {time_column}")
            print(f"  - Values column: {values_column}")
            print(f"  - Values label: {values_label}")
            print("="*70 + "\n")

        except Exception as e:
            print(f"[WARN] Auto-detection failed: {e}")
            print("Falling back to defaults: time=0, values=1, skip=0\n")
            from .constants import (
                DEFAULT_TIME_COLUMN, DEFAULT_VALUES_COLUMN,
                DEFAULT_SKIP_ROWS, DEFAULT_VALUES_LABEL
            )
            time_column = DEFAULT_TIME_COLUMN
            values_column = DEFAULT_VALUES_COLUMN
            values_label = DEFAULT_VALUES_LABEL
            skip_rows = DEFAULT_SKIP_ROWS
    else:
        from .constants import (
            DEFAULT_TIME_COLUMN, DEFAULT_VALUES_COLUMN,
            DEFAULT_SKIP_ROWS, DEFAULT_VALUES_LABEL
        )
        time_column = DEFAULT_TIME_COLUMN
        values_column = DEFAULT_VALUES_COLUMN
        values_label = DEFAULT_VALUES_LABEL
        skip_rows = DEFAULT_SKIP_ROWS
        print(f"[STEP 2] Using default structure: time=0, values=1, skip=0\n")
    
    # Step 3: Determine chunk counter (append or overwrite)
    print("[STEP 3] Checking existing database files...")
    existing_files = list(database_label_dir.glob(f"{classification_label}_*.csv"))
    
    if APPEND_MODE and existing_files:
        existing_numbers = []
        for f in existing_files:
            try:
                num_str = f.stem.split('_')[-1]
                existing_numbers.append(int(num_str))
            except (ValueError, IndexError):
                continue
        
        if existing_numbers:
            chunk_counter = max(existing_numbers) + 1
            print(f"[OK] Found {len(existing_files)} existing files")
            print(f"  Append mode: Starting from chunk {chunk_counter}\n")
        else:
            chunk_counter = CHUNK_COUNTER_START
    else:
        chunk_counter = CHUNK_COUNTER_START
        if not APPEND_MODE and existing_files:
            print(f"[WARN] Overwrite mode: Will replace existing files\n")
    
    starting_counter = chunk_counter
    
    # Calculate interpolation parameters
    total_duration = chunk_duration + 2 * padding_duration
    interpolated_time = np.arange(0, total_duration + time_interval/2, time_interval)
    interpolated_time = interpolated_time[interpolated_time <= total_duration]
    
    # Step 4: Process CSV files
    print("[STEP 4] Processing CSV files into chunks...")
    print("="*70)
    
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, skiprows=skip_rows, header=None)
            time = df.iloc[:, time_column].values
            values = df.iloc[:, values_column].values
            
            if len(time) < MIN_DATA_POINTS:
                print(f"{LOG_FORMAT_SKIP} {csv_file.name}: insufficient data points")
                continue
            
            dt = np.mean(np.diff(time))
            if dt <= 0:
                print(f"{LOG_FORMAT_SKIP} {csv_file.name}: invalid time intervals")
                continue
            
            sampling_rate = 1.0 / dt
            samples_per_chunk = int(chunk_duration * sampling_rate)
            
            if samples_per_chunk <= 0:
                print(f"{LOG_FORMAT_SKIP} {csv_file.name}: invalid chunk size")
                continue
            
            num_chunks = int(np.floor(len(time) / samples_per_chunk))
            
            if num_chunks == 0:
                print(f"{LOG_FORMAT_SKIP} {csv_file.name}: insufficient data for one chunk")
                continue
            
            for i in range(num_chunks):
                chunk_start = i * samples_per_chunk
                chunk_end = chunk_start + samples_per_chunk
                
                if chunk_end > len(time):
                    break
                
                time_chunk = time[chunk_start:chunk_end]
                values_chunk = values[chunk_start:chunk_end]
                time_chunk_normalized = time_chunk - time_chunk[0]
                
                # Create padding regions with multiple points for flat zero segments
                # Start padding: 0 to padding_duration (zeros)
                # Data region: padding_duration to padding_duration + chunk_duration
                # End padding: padding_duration + chunk_duration to total_duration (zeros)

                num_padding_points = max(2, int(padding_duration / time_interval))

                # Start padding times and values (flat zeros from 0 to padding_duration)
                start_padding_time = np.linspace(0, padding_duration, num_padding_points, endpoint=False)
                start_padding_values = np.zeros(num_padding_points)

                # Data region (shifted by padding_duration)
                data_time = time_chunk_normalized + padding_duration

                # End padding times and values (flat zeros from chunk_end to total_duration)
                end_padding_start = padding_duration + chunk_duration
                end_padding_time = np.linspace(end_padding_start, total_duration, num_padding_points + 1)
                end_padding_values = np.zeros(num_padding_points + 1)

                time_with_padding = np.concatenate([
                    start_padding_time,
                    data_time,
                    end_padding_time
                ])

                values_with_padding = np.concatenate([
                    start_padding_values,
                    values_chunk,
                    end_padding_values
                ])
                
                interpolator = interp1d(
                    time_with_padding,
                    values_with_padding,
                    kind=INTERPOLATION_KIND,
                    bounds_error=INTERPOLATION_BOUNDS_ERROR,
                    fill_value=INTERPOLATION_FILL_VALUE
                )
                
                interpolated_values = interpolator(interpolated_time)
                
                output_filename = CHUNK_FILENAME_TEMPLATE.format(
                    label=classification_label,
                    counter=chunk_counter
                )
                output_path = database_label_dir / output_filename
                
                with open(output_path, 'w') as f:
                    f.write(f"{classification_label}\n")
                    f.write(f"Time(s),{values_label}\n")
                    for t, v in zip(interpolated_time, interpolated_values):
                        f.write(f"{t:.6f},{v:.6f}\n")
                
                chunk_counter += 1
            
            relative_path = csv_file.relative_to(import_folder)
            print(f"{LOG_FORMAT_OK} Processed: {relative_path} ({num_chunks} chunks)")
            
        except Exception as e:
            relative_path = csv_file.relative_to(import_folder)
            print(f"{LOG_FORMAT_ERROR} {relative_path}: {str(e)}")
    
    total_chunks = chunk_counter - starting_counter
    
    # Step 5: Generate metadata
    if GENERATE_METADATA:
        print(f"\n[STEP 5] Generating metadata files...")
        
        # Database metadata
        db_metadata = generate_database_metadata(
            label=classification_label,
            csv_files=csv_files,
            source_folder=import_folder,
            database_label_dir=database_label_dir,
            time_column=time_column,
            values_column=values_column,
            values_label=values_label,
            skip_rows=skip_rows,
            time_interval=time_interval,
            chunk_duration=chunk_duration,
            padding_duration=padding_duration,
            total_chunks=total_chunks,
            chunk_range=(starting_counter, chunk_counter - 1)
        )
        save_metadata(db_metadata, database_label_dir / METADATA_FILENAME)
        
        # Raw database metadata
        if COPY_RAW_DATA and raw_database_import_dir.exists():
            raw_metadata = generate_raw_database_metadata(
                import_folder_name=import_folder.name,
                source_path=import_folder,
                csv_files=csv_files,
                subfolder_structure=subfolders
            )
            save_metadata(raw_metadata, raw_database_import_dir / METADATA_FILENAME)
    
    # Final summary
    print(f"\n{'='*70}")
    print(f"INGESTION COMPLETE")
    print(f"{'='*70}")
    print(f"Source files processed: {len(csv_files)}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Chunk range: {classification_label}_{starting_counter:04d} to {classification_label}_{chunk_counter-1:04d}")
    print(f"Processed data: {database_label_dir.resolve()}")
    if COPY_RAW_DATA:
        print(f"Raw data backup: {raw_database_import_dir.resolve()}")
    print(f"Each chunk: {len(interpolated_time)} samples, {interpolated_time[0]:.1f}s to {interpolated_time[-1]:.1f}s")
    print(f"Time interval: {time_interval}s")
    print(f"{'='*70}")

if __name__ == "__main__":
    # Example usage - edit paths and labels for your data
    ingest_sensor_data(
        import_folder_path="../../imports/normal_data",
        classification_label="normal"
    )