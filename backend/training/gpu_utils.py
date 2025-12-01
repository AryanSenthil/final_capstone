"""
gpu_utils.py — GPU memory management utilities.

Provides functions for:
- Configuring GPU memory growth
- Clearing GPU memory
- Handling GPU OOM errors
"""

import gc
import tensorflow as tf
from typing import Optional


def configure_gpu_memory(memory_limit_mb: Optional[int] = None, enable_growth: bool = True):
    """
    Configure GPU memory settings to prevent OOM errors.

    Args:
        memory_limit_mb: Maximum memory limit in MB (None for no limit)
        enable_growth: If True, allocate GPU memory as needed

    Returns:
        bool: True if GPU configured successfully, False otherwise
    """
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            for gpu in gpus:
                if enable_growth:
                    tf.config.experimental.set_memory_growth(gpu, True)
                    print(f"[GPU] Enabled memory growth for {gpu.name}")

                if memory_limit_mb:
                    tf.config.set_logical_device_configuration(
                        gpu,
                        [tf.config.LogicalDeviceConfiguration(memory_limit=memory_limit_mb)]
                    )
                    print(f"[GPU] Set memory limit to {memory_limit_mb}MB for {gpu.name}")

            return True
        else:
            print("[GPU] No GPU devices found. Running on CPU.")
            return False
    except RuntimeError as e:
        print(f"[GPU WARNING] Failed to configure GPU: {e}")
        print("[GPU] This may happen if GPU is already initialized.")
        return False


def clear_gpu_memory():
    """
    Clear GPU memory by clearing Keras session and running garbage collection.
    Call this after training to free up GPU memory.
    """
    try:
        # Clear Keras backend session
        tf.keras.backend.clear_session()

        # Force garbage collection
        gc.collect()

        print("[GPU] Cleared GPU memory and Keras session")
    except Exception as e:
        print(f"[GPU WARNING] Error clearing GPU memory: {e}")


def get_gpu_memory_info():
    """
    Get current GPU memory usage information.

    Returns:
        dict: GPU memory info or None if no GPU available
    """
    try:
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            return None

        # TensorFlow doesn't provide direct memory usage API
        # This would require nvidia-smi or other tools
        return {
            "gpu_count": len(gpus),
            "gpu_names": [gpu.name for gpu in gpus]
        }
    except Exception as e:
        print(f"[GPU WARNING] Error getting GPU info: {e}")
        return None


def handle_gpu_oom_error(error: Exception) -> str:
    """
    Generate user-friendly error message for GPU OOM errors.

    Args:
        error: The exception that was raised

    Returns:
        str: User-friendly error message with suggestions
    """
    error_msg = str(error).lower()

    if "out of memory" in error_msg or "oom" in error_msg:
        return """
GPU Memory Error: Out of Memory

Your GPU has run out of memory. Here are some solutions:

1. Close other programs using the GPU
2. Reduce the batch size in settings
3. Use a smaller time window (e.g., 1s or 2s instead of 10s)
4. Clear GPU memory by restarting the backend server

To manually clear GPU memory, run:
  nvidia-smi
  kill -9 <process_id>

Or restart the backend server to release all GPU memory.
"""

    return f"GPU Error: {str(error)}"


def setup_mixed_precision():
    """
    Enable mixed precision training to reduce memory usage.
    Uses float16 for computation and float32 for variables.
    """
    try:
        policy = tf.keras.mixed_precision.Policy('mixed_float16')
        tf.keras.mixed_precision.set_global_policy(policy)
        print("[GPU] Enabled mixed precision training (float16)")
        return True
    except Exception as e:
        print(f"[GPU WARNING] Could not enable mixed precision: {e}")
        return False
