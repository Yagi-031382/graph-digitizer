import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from graph_digitizer.app import MainWindow, main


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_image_click_recalibrate_export_and_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            image = QImage(640, 480, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.white)
            for extension in ("png", "jpg"):
                path = Path(folder) / f"画像.{extension}"
                self.assertTrue(image.save(str(path)))
                window = MainWindow()
                window.show()
                self.application.processEvents()
                self.assertTrue(window.load_image(path))
                for key, point in zip(("x_min", "x_max", "y_min", "y_max"),
                                      ((100, 400), (500, 400), (100, 400), (100, 100))):
                    window.values[key].setValue({"x_min":0, "x_max":40, "y_min":0, "y_max":6}[key])
                    window.on_image_click(*point)
                self.assertEqual(window.mode.currentData(), "curve")
                window.view.scale(1.2, 1.2)
                self.application.processEvents()
                target = window.view.mapFromScene(QPointF(300, 250))
                QTest.mouseClick(window.view.viewport(), Qt.MouseButton.LeftButton, pos=target)
                self.assertEqual(len(window.points), 1)
                x, y = window.calibration().to_graph(window.points[0])
                self.assertAlmostEqual(x, 20, delta=0.15)
                self.assertAlmostEqual(y, 3, delta=0.025)
                window.values["x_max"].setValue(80)
                self.assertAlmostEqual(float(window.table.item(0, 2).text()), 40, delta=0.3)
                csv = Path(folder) / f"result-{extension}.csv"
                with patch("graph_digitizer.app.QFileDialog.getSaveFileName", return_value=(str(csv), "CSV")):
                    window.export()
                self.assertTrue(csv.exists())
                self.assertFalse(window.dirty)
                self.assertAlmostEqual(pd.read_csv(csv).iloc[0]["x"], 40, delta=0.3)
                window.plot.draw()
                self.assertEqual(len(window.plot.axes.lines[0].get_xdata()), 1)
                window.table.selectRow(0)
                window.remove_selected()
                self.assertEqual(window.points, [])
                window.dirty = False
                window.close()

    def test_missing_calibration_rejects_click_and_export(self):
        window = MainWindow()
        with patch("graph_digitizer.app.QMessageBox.warning") as warning:
            window.on_image_click(100, 100)
            window.export()
            self.assertEqual(warning.call_count, 2)
            self.assertEqual(window.points, [])
        window.close()


if __name__ == "__main__":
    unittest.main()
