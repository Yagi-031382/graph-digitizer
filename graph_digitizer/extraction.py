"""Foreground segmentation and curve candidates inside calibrated axes."""
from dataclasses import dataclass
import cv2
import numpy as np
from .calibration import Calibration, Pixel


@dataclass
class CurveCandidate:
    name: str
    points: list[Pixel]
    span: int


def extract_curves(rgb: np.ndarray, calibration: Calibration, gap_px=12) -> list[CurveCandidate]:
    """Input: uint8 RGB raster, calibration, gap distance in px. Output: curve candidates with source px points.

    White background, linear upright axes, and single-valued y(x) are assumed.
    Dilation groups dashed components, but coordinates come only from original foreground pixels.
    """
    calibration.validate()
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("RGB画像（各成分がuint8）が必要である。")
    if not 0 <= gap_px <= 100:
        raise ValueError("接続距離は0～100 pxで指定する必要がある。")
    height, width = rgb.shape[:2]
    x0, x1 = sorted((calibration.pixels["x_min"][0], calibration.pixels["x_max"][0]))
    y0, y1 = sorted((calibration.pixels["y_min"][1], calibration.pixels["y_max"][1]))
    left, right = max(0, int(np.ceil(x0))+3), min(width, int(np.floor(x1))-2)
    top, bottom = max(0, int(np.ceil(y0))+3), min(height, int(np.floor(y1))-2)
    if right-left < 10 or bottom-top < 10:
        raise ValueError("軸で囲まれた抽出範囲が不足している。基準点を確認する必要がある。")
    crop = np.ascontiguousarray(rgb[top:bottom, left:right])
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    threshold, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    hue, saturation, _ = cv2.split(hsv)
    masks = [("黒・灰色", ((saturation < 60) & (gray <= min(threshold, 200))).astype(np.uint8))]
    for index, name in enumerate(("赤", "黄", "緑", "水色", "青", "紫")):
        # Hue has range 0..179; red wraps around its origin.
        shifted = (hue.astype(np.int16) + 15) % 180
        masks.append((name, ((shifted//30 == index) & (saturation >= 60) & (gray < 245)).astype(np.uint8)))
    candidates = []
    for color_name, mask in masks:
        if not mask.any():
            continue
        if color_name == "黒・灰色":
            # Remove only nearly full-width/full-height straight grid lines.
            horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((1, max(10, int(mask.shape[1]*0.8))), np.uint8))
            vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((max(10, int(mask.shape[0]*0.8)), 1), np.uint8))
            mask = mask & ~(horizontal | vertical)
        kernel_size = int(gap_px)+1
        groups = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))) if gap_px else mask
        count, labels, stats, _ = cv2.connectedComponentsWithStats(groups, 8)
        for label in range(1, count):
            gx, gy, gw, gh, _ = stats[label]
            region = (labels[gy:gy+gh, gx:gx+gw] == label) & (mask[gy:gy+gh, gx:gx+gw] != 0)
            rows, columns = np.nonzero(region)
            if len(columns) < 20 or not len(columns):
                continue
            span = int(columns.max()-columns.min()+1)
            if span < max(12, int(mask.shape[1]*0.05)):
                continue
            points = []
            for column in np.unique(columns):
                # Center of the line thickness; missing columns are not synthesized.
                row = float(np.median(rows[columns == column]))
                points.append((float(left+gx+column), float(top+gy+row)))
            points.sort(key=lambda p: calibration.to_graph(p)[0])
            candidates.append(CurveCandidate(f"{color_name} / {span} px / {len(points)} 点", points, span))
    candidates.sort(key=lambda candidate: (candidate.span, len(candidate.points)), reverse=True)
    return candidates
