"""CSV loading and comparison interface, independent of image calibration."""
from pathlib import Path
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
    QLineEdit, QLabel, QListWidget, QFileDialog, QMessageBox,
)
from .plot_view import PlotView


def load_curve(path):
    """Input: CSV path. Output: numeric x/y DataFrame in file order; invalid CSV raises ValueError."""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if not {"x", "y"}.issubset(frame.columns):
        raise ValueError("x列とy列が必要である。")
    if frame.empty:
        raise ValueError("データ行が存在しない。")
    frame = frame[["x", "y"]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        raise ValueError("x列とy列には空欄・NaN・無限大を含まない数値が必要である。")
    return frame


class ComparisonPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.curves = {}  # resolved path -> DataFrame, insertion order is preserved
        self.plot = PlotView()
        self.files = QListWidget()
        self.files.setMaximumHeight(110)
        self.show_points = QCheckBox("点を表示（OFF：線のみ）")
        self.show_points.setChecked(False)
        self.x_label = QLineEdit("Strain [%]")
        self.y_label = QLineEdit("Stress [MPa]")
        layout = QVBoxLayout(self)
        buttons = QHBoxLayout()
        for label, action in (("CSVを追加（複数選択可）", self.open_csvs),
                              ("選択CSVを除外", self.remove_selected)):
            button = QPushButton(label)
            button.clicked.connect(action)
            buttons.addWidget(button)
        buttons.addWidget(self.show_points)
        layout.addLayout(buttons)
        layout.addWidget(self.files)
        labels = QHBoxLayout()
        labels.addWidget(QLabel("x軸名・単位"))
        labels.addWidget(self.x_label)
        labels.addWidget(QLabel("y軸名・単位"))
        labels.addWidget(self.y_label)
        layout.addLayout(labels)
        layout.addWidget(QLabel("%：元の試料長に対する変形量の百分率。MPa：応力、1 MPa = 10⁶ N/m²。単位の換算は行わない。"))
        layout.addWidget(self.plot, 1)
        self.show_points.toggled.connect(self.refresh)
        self.x_label.textChanged.connect(self.refresh)
        self.y_label.textChanged.connect(self.refresh)
        self.refresh()

    def open_csvs(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "比較するCSVを選択", "", "CSV (*.csv *.CSV)")
        if paths:
            self.add_csvs(paths)

    def add_csvs(self, paths):
        """Input: CSV paths. Output: error strings; valid curves are added or refreshed."""
        errors = []
        for filename in paths:
            path = Path(filename).resolve()
            try:
                frame = load_curve(path)
            except (OSError, ValueError, UnicodeError) as error:
                errors.append(f"{path.name}: {error}")
                continue
            self.curves[path] = frame
        self.files.clear()
        for path in self.curves:
            self.files.addItem(path.name)
            self.files.item(self.files.count()-1).setToolTip(str(path))
        self.refresh()
        if errors:
            QMessageBox.warning(self, "CSV読込エラー", "\n".join(errors))
        return errors

    def remove_selected(self):
        row = self.files.currentRow()
        if row >= 0:
            del self.curves[list(self.curves)[row]]
            self.files.takeItem(row)
            self.refresh()

    def refresh(self):
        """Input: loaded curves and controls. Output: updated comparison plot; None."""
        self.plot.compare([(p.name, frame) for p, frame in self.curves.items()],
                          self.x_label.text(), self.y_label.text(), self.show_points.isChecked())
