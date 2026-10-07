"""Data storage and CSV export; pixel points remain available for recalibration."""
from pathlib import Path
import pandas as pd
from .calibration import Calibration, Pixel


def make_frame(points: list[Pixel], calibration: Calibration) -> pd.DataFrame:
    """Input: image points in px and calibration. Output: x/y DataFrame in click order."""
    calibration.validate()
    return pd.DataFrame([calibration.to_graph(p) for p in points], columns=["x", "y"])


def save_csv(path: str | Path, points: list[Pixel], calibration: Calibration) -> None:
    """Input: destination, px points, calibration. Output: UTF-8 BOM CSV; returns None."""
    make_frame(points, calibration).to_csv(path, index=False, encoding="utf-8-sig", float_format="%.12g")
