import unittest
import tempfile
from pathlib import Path
import pandas as pd
from graph_digitizer.calibration import Calibration
from graph_digitizer.data import save_csv


def example():
    return Calibration({"x_min": (100, 400), "x_max": (500, 400),
                        "y_min": (100, 400), "y_max": (100, 100)},
                       {"x_min": 0, "x_max": 40, "y_min": 0, "y_max": 6})


class ConversionTests(unittest.TestCase):
    def test_known_points_and_extrapolation(self):
        c = example()
        self.assertEqual(c.to_graph((100, 400)), (0, 0))
        self.assertEqual(c.to_graph((500, 100)), (40, 6))
        self.assertEqual(c.to_graph((300, 250)), (20, 3))
        self.assertEqual(c.to_graph((600, 50)), (50, 7))

    def test_nonzero_origin(self):
        c = example()
        c.values.update(x_min=-10, x_max=30, y_min=2, y_max=8)
        self.assertEqual(c.to_graph((300, 250)), (10, 5))

    def test_invalid_references(self):
        for change in (lambda c: c.pixels.pop("x_min"),
                       lambda c: c.pixels.update(x_max=(100, 200)),
                       lambda c: c.pixels.update(y_max=(200, 400)),
                       lambda c: c.values.update(x_max=0),
                       lambda c: c.values.update(y_min=float("nan"))):
            c = example()
            change(c)
            with self.assertRaises(ValueError):
                c.to_graph((300, 250))

    def test_csv_values_order_and_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "曲線.csv"
            save_csv(path, [(500, 100), (300, 250)], example())
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
            frame = pd.read_csv(path)
            self.assertEqual(list(frame.columns), ["x", "y"])
            self.assertEqual(frame.values.tolist(), [[40, 6], [20, 3]])
