"""
Settings API Module

Connects frontend settings dialog to backend configuration files.
Handles time window / sampling rate coupling automatically.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Literal
from pathlib import Path

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Path to settings module
SETTINGS_DIR = Path(__file__).parent / "settings"
CONFIGS_FILE = SETTINGS_DIR / "configs.py"
CONSTANTS_FILE = SETTINGS_DIR / "constants.py"

# Time window configuration mapping
# Each time window has: sampling_rate (maintains 16,000 total samples), chunk_duration, padding_duration
# Formula: time_window = padding + chunk + padding
TIME_WINDOW_CONFIG: dict[int, dict] = {
    1: {"sampling_rate": 16000, "chunk_duration": 0.6, "padding_duration": 0.2},
    2: {"sampling_rate": 8000, "chunk_duration": 1.2, "padding_duration": 0.4},
    5: {"sampling_rate": 3200, "chunk_duration": 3.0, "padding_duration": 1.0},
    10: {"sampling_rate": 1600, "chunk_duration": 8.0, "padding_duration": 1.0},
}

# Epoch presets
EPOCH_PRESETS: dict[str, int] = {
    "quick": 300,
    "standard": 1000,
    "thorough": 2000,
}


class SettingsUpdate(BaseModel):
    """Request model for settings updates."""
    time_window: Literal[1, 2, 5, 10] | None = None
    training_duration: Literal["quick", "standard", "thorough"] | None = None
    data_split: Literal[0.1, 0.15, 0.2, 0.3] | None = None  # validation_split value


class SettingsResponse(BaseModel):
    """Response model for current settings."""
    time_window: int
    sampling_rate: int
    epochs: int
    validation_split: float


class ApiKeyUpdate(BaseModel):
    """Request model for API key update."""
    api_key: str


def _read_file(path: Path) -> str:
    """Read a Python config file."""
    return path.read_text()


def _write_file(path: Path, content: str) -> None:
    """Write content to a Python config file."""
    path.write_text(content)


def _update_value(content: str, var_name: str, new_value: int | float) -> str:
    """Replace a variable assignment in Python source code."""
    import re
    pattern = rf"^({var_name}\s*=\s*)[\d.]+(.*)$"
    replacement = rf"\g<1>{new_value}\2"
    updated = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    return updated


@router.get("", response_model=SettingsResponse)
async def get_settings() -> SettingsResponse:
    """Retrieve current settings from config files."""
    from settings import configs, constants

    # Reverse lookup for time window from sampling rate
    time_window = next(
        (t for t, cfg in TIME_WINDOW_CONFIG.items() if cfg["sampling_rate"] == constants.TRAINING_SAMPLING_RATE),
        10  # default
    )

    return SettingsResponse(
        time_window=time_window,
        sampling_rate=constants.TRAINING_SAMPLING_RATE,
        epochs=configs.CNN_EPOCHS,
        validation_split=constants.VALIDATION_SPLIT,
    )


@router.patch("", response_model=SettingsResponse)
async def update_settings(updates: SettingsUpdate) -> SettingsResponse:
    """
    Update settings in config files.

    Time window changes automatically update sampling rate, chunk duration, and padding.
    """
    try:
        # Update constants.py if needed
        if updates.time_window is not None or updates.data_split is not None:
            content = _read_file(CONSTANTS_FILE)

            if updates.time_window is not None:
                config = TIME_WINDOW_CONFIG[updates.time_window]
                content = _update_value(content, "TRAINING_TIME_PERIOD", updates.time_window)
                content = _update_value(content, "TRAINING_SAMPLING_RATE", config["sampling_rate"])

            if updates.data_split is not None:
                content = _update_value(content, "VALIDATION_SPLIT", updates.data_split)

            _write_file(CONSTANTS_FILE, content)

        # Update configs.py if needed (epochs and chunk/padding for time window)
        configs_updated = False
        content = _read_file(CONFIGS_FILE)

        if updates.training_duration is not None:
            epochs = EPOCH_PRESETS[updates.training_duration]
            content = _update_value(content, "CNN_EPOCHS", epochs)
            content = _update_value(content, "RESNET_EPOCHS", epochs)
            configs_updated = True

        if updates.time_window is not None:
            config = TIME_WINDOW_CONFIG[updates.time_window]
            content = _update_value(content, "DB_CHUNK_DURATION", config["chunk_duration"])
            content = _update_value(content, "DB_PADDING_DURATION", config["padding_duration"])
            configs_updated = True

        if configs_updated:
            _write_file(CONFIGS_FILE, content)

        # Reload modules to reflect changes
        import importlib
        from settings import configs, constants
        importlib.reload(constants)
        importlib.reload(configs)

        return await get_settings()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e}")


@router.post("/api-key")
async def update_api_key(update: ApiKeyUpdate):
    """
    Update OpenAI API key in environment.
    This endpoint stores the API key temporarily in memory for the current session.
    """
    import os
    from openai import OpenAI

    try:
        # Set the environment variable
        os.environ["OPENAI_API_KEY"] = update.api_key

        # Reinitialize the OpenAI client in api.py
        import api
        api.openai_client = OpenAI(api_key=update.api_key) if update.api_key else None

        return {"success": True, "message": "API key updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update API key: {e}")