import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from graph_digitizer.app import MainWindow
from graph_digitizer.comparison import load_curve


class ComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_overlay_names_colors_markers_removal_and_mode_state(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / name for name in ("H1.csv", "H2.csv")]
            for path, data in zip(paths, ("x,y\n0.2,3\n0.1,1\n", "x,y\n0.1,2\n0.3,4\n")):
                path.write_text(data, encoding="utf-8-sig")
            window = MainWindow()
            window.points = [(100, 200)]
            window.dirty = True
            window.tabs.setCurrentIndex(1)
            page = window.comparison
            with patch("graph_digitizer.comparison.QFileDialog.getOpenFileNames", return_value=([str(p) for p in paths], "CSV")):
                page.open_csvs()
            lines = page.plot.axes.lines
            self.assertEqual([line.get_label() for line in lines], ["H1.csv", "H2.csv"])
            self.assertNotEqual(lines[0].get_color(), lines[1].get_color())
            self.assertEqual(list(lines[0].get_xdata()), [0.2, 0.1])
            self.assertTrue(all(line.get_marker() in (None, "None") for line in lines))
            page.show_points.setChecked(True)
            self.assertTrue(all(line.get_marker() == "o" for line in page.plot.axes.lines))
            page.show_points.setChecked(False)
            self.assertTrue(all(line.get_marker() in (None, "None") for line in page.plot.axes.lines))
            page.plot.draw()
            page.add_csvs([str(paths[0])])
            self.assertEqual(len(page.curves), 2)
            page.files.setCurrentRow(0)
            page.remove_selected()
            self.assertEqual(len(page.plot.axes.lines), 1)
            self.assertTrue(paths[0].exists())
            window.tabs.setCurrentIndex(0)
            self.assertEqual(window.points, [(100, 200)])
            self.assertTrue(window.dirty)
            window.dirty = False
            window.close()

    def test_invalid_csv_does_not_replace_valid_curves(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "curve.csv"
            path.write_text("x,y\n0,1\n")
            window = MainWindow()
            page = window.comparison
            self.assertEqual(page.add_csvs([path]), [])
            for data in ("a,b\n1,2\n", "x,y\n", "x,y\nfoo,1\n", "x,y\n,1\n", "x,y\ninf,1\n"):
                path.write_text(data)
                with self.assertRaises(ValueError):
                    load_curve(path)
                with patch("graph_digitizer.comparison.QMessageBox.warning") as warning:
                    self.assertTrue(page.add_csvs([path]))
                    warning.assert_called_once()
                self.assertEqual(page.plot.axes.lines[0].get_ydata().tolist(), [1])
            window.close()
