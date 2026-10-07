"""Coordinate conversion independent of GUI and extraction method."""
from dataclasses import dataclass
import math

Pixel = tuple[float, float]
KEYS = ("x_min", "x_max", "y_min", "y_max")


@dataclass(frozen=True)
class Calibration:
    pixels: dict[str, Pixel]
    values: dict[str, float]

    def validate(self) -> None:
        """Input: stored axis references. Output: None; invalid references raise ValueError."""
        if any(k not in self.pixels or k not in self.values for k in KEYS):
            raise ValueError("軸の基準点をすべて指定する必要がある。")
        if not all(math.isfinite(n) for p in self.pixels.values() for n in p):
            raise ValueError("ピクセル座標は有限値である必要がある。")
        if not all(math.isfinite(n) for n in self.values.values()):
            raise ValueError("軸値は有限値である必要がある。")
        if self.pixels["x_max"][0] == self.pixels["x_min"][0]:
            raise ValueError("x軸の基準点は異なる水平位置に指定する必要がある。")
        if self.pixels["y_max"][1] == self.pixels["y_min"][1]:
            raise ValueError("y軸の基準点は異なる垂直位置に指定する必要がある。")
        for axis in ("x", "y"):
            if self.values[f"{axis}_max"] <= self.values[f"{axis}_min"]:
                raise ValueError(f"{axis}軸の最大値は最小値を超える必要がある。")

    def to_graph(self, pixel: Pixel) -> tuple[float, float]:
        """Input: original image (u, v) in px. Output: (x, y) in chosen axis units."""
        self.validate()
        if not all(math.isfinite(n) for n in pixel):
            raise ValueError("ピクセル座標は有限値である必要がある。")
        u, v = pixel
        u0, u1 = self.pixels["x_min"][0], self.pixels["x_max"][0]
        v0, v1 = self.pixels["y_min"][1], self.pixels["y_max"][1]
        x0, x1 = self.values["x_min"], self.values["x_max"]
        y0, y1 = self.values["y_min"], self.values["y_max"]
        return (x0 + (u-u0)/(u1-u0)*(x1-x0),
                y0 + (v-v0)/(v1-v0)*(y1-y0))
