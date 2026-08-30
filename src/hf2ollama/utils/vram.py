"""VRAM detection and quantization recommendation."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


QUANT_MULTIPLIERS = {
    "Q2_K": 0.31,
    "Q3_K_M": 0.44,
    "Q4_K_M": 0.56,
    "Q5_K_M": 0.68,
    "Q6_K": 0.81,
    "Q8_0": 1.0,
}


@dataclass
class VRAMInfo:
    """GPU VRAM information from nvidia-smi."""

    available_gb: float
    gpu_name: str = "Unknown"


def detect_vram() -> VRAMInfo | None:
    """Detect available GPU VRAM using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total,name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            line = result.stdout.strip().splitlines()[0]
            parts = line.split(",")
            vram_mb = float(parts[0].strip())
            name = parts[1].strip() if len(parts) > 1 else "NVIDIA GPU"
            return VRAMInfo(available_gb=vram_mb / 1024, gpu_name=name)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def recommend_quant(model_params_b: float, vram_gb: float) -> list[str]:
    """Recommend quantizations that fit in the given VRAM.

    Args:
        model_params_b: Model parameter count in billions (e.g., 7.0 for 7B).
        vram_gb: Available VRAM in GB.

    Returns:
        List of quantization names that should fit, from smallest to largest.

    """
    fits = []
    for quant, multiplier in sorted(QUANT_MULTIPLIERS.items(), key=lambda x: x[1]):
        estimated_gb = model_params_b * multiplier * 1.1
        if estimated_gb <= vram_gb:
            fits.append(quant)

    return fits
