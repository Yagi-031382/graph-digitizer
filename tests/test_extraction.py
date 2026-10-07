import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
import pandas as pd
from PySide6.QtWidgets import QApplication, QMessageBox
from graph_digitizer.calibration import Calibration
from graph_digitizer.extraction import extract_curves
from graph_digitizer.app import MainWindow


def calibrated():
    return Calibration({"x_min": (20, 220), "x_max": (320, 220),
                        "y_min": (20, 220), "y_max": (20, 20)},
                       {"x_min": 0, "x_max": 30, "y_min": 0, "y_max": 4})


def graph(color=(0, 0, 0), dashed=False):
    rgb = np.full((240, 340, 3), 255, np.uint8)
    cv2.line(rgb, (20, 20), (20, 220), (0, 0, 0), 2)
    cv2.line(rgb, (20, 220), (320, 220), (0, 0, 0), 2)
    for x in range(40, 291):
        if not dashed or (x-40) % 20 < 14:
            y = int(round(190 - (x-40)*0.5))
            cv2.circle(rgb, (x, y), 1, color, -1)
    return rgb


class ExtractionTests(unittest.TestCase):
    def test_black_and_dashed_curve_coordinates(self):
        for dashed in (False, True):
            curves = extract_curves(graph(dashed=dashed), calibrated(), gap_px=12)
            self.assertTrue(curves)
            points = curves[0].points
            self.assertGreater(len(points), 160)
            for x, y in points:
                self.assertAlmostEqual(y, 190-(x-40)*0.5, delta=1.1)
            if dashed:
                self.assertTrue(any(points[i+1][0]-points[i][0] > 1 for i in range(len(points)-1)))

    def test_two_colors_are_separate_candidates(self):
        rgb = graph((255, 0, 0))
        cv2.line(rgb, (40, 60), (290, 90), (0, 0, 255), 2)
        curves = extract_curves(rgb, calibrated())
        self.assertEqual(len(curves), 2)
        self.assertTrue(any(c.name.startswith("赤") for c in curves))
        self.assertTrue(any(c.name.startswith("青") for c in curves))

    def test_grid_removed_and_blank_returns_no_candidates(self):
        rgb = graph()
        cv2.line(rgb, (20, 100), (320, 100), (130, 130, 130), 1)
        curves = extract_curves(rgb, calibrated())
        self.assertTrue(curves)
        self.assertLess(sum(abs(y-100) < 0.1 for x, y in curves[0].points), 10)
        self.assertEqual(extract_curves(np.full_like(rgb, 255), calibrated()), [])

    def test_gui_detection_export_preservation_and_calibration_reset(self):
        application = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "曲線.png"
            cv2.imencode(".png", cv2.cvtColor(graph(dashed=True), cv2.COLOR_RGB2BGR))[1].tofile(path)
            window = MainWindow()
            self.assertTrue(window.load_image(path))
            calibration = calibrated()
            for key, value in calibration.values.items():
                window.values[key].setValue(value)
            window.references = dict(calibration.pixels)
            window.detect_curves()
            self.assertGreater(len(window.points), 160)
            previous = list(window.points)
            with patch("graph_digitizer.app.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
                window.detect_curves()
            self.assertEqual(window.points, previous)
            csv = Path(folder) / "curve.csv"
            with patch("graph_digitizer.app.QFileDialog.getSaveFileName", return_value=(str(csv), "CSV")):
                window.export()
            frame = pd.read_csv(csv)
            self.assertEqual(len(frame), len(window.points))
            self.assertTrue(frame.x.is_monotonic_increasing)
            window.comparison.add_csvs([csv])
            self.assertEqual(len(window.comparison.plot.axes.lines[0].get_xdata()), len(frame))
            window.values["x_max"].setValue(60)
            self.assertEqual(window.candidates, [])
            window.dirty = False
            window.close()
