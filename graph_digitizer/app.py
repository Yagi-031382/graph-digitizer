"""GUI orchestration; extraction code supplies original-image pixel points."""
import sys
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QDoubleSpinBox, QLineEdit,
    QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox,
    QSplitter, QAbstractItemView,
)
from .calibration import Calibration, KEYS
from .data import make_frame, save_csv
from .image_view import ImageView
from .plot_view import PlotView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("graph-digitizer — 手動グラフ抽出")
        self.resize(1400, 900)
        self.references = {}
        self.points = []
        self.image_path = None
        self.dirty = False
        self.view = ImageView()
        self.plot = PlotView()
        self.mode = QComboBox()
        self.mode.addItem("曲線のデータ点を取得", "curve")
        for key, label in zip(KEYS, ("x軸最小点", "x軸最大点", "y軸最小点", "y軸最大点")):
            self.mode.addItem(label + "を指定", key)
        self.values = {}
        self.reference_labels = {}
        self.x_label = QLineEdit("Strain [%]")
        self.y_label = QLineEdit("Stress [MPa]")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["u [px]", "v [px]", "x [%]", "y [MPa]"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        central = QWidget()
        layout = QVBoxLayout(central)
        buttons = QHBoxLayout()
        for label, action in (("画像を開く", self.open_image), ("画像全体を表示", self.view.fit_image),
                              ("選択点を削除", self.remove_selected), ("最後の点を戻す", self.undo),
                              ("CSV保存", self.export)):
            button = QPushButton(label)
            button.clicked.connect(action)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        layout.addWidget(QLabel("モードを選び、画像を左クリックする。ホイールで拡大・縮小、スクロールバーで移動。"))
        layout.addWidget(self.mode)
        references_layout = QHBoxLayout()
        for key, label, default in zip(KEYS, ("x最小", "x最大", "y最小", "y最大"), (0, 100, 0, 1)):
            column = QVBoxLayout()
            column.addWidget(QLabel(label + "の軸値"))
            value = QDoubleSpinBox()
            value.setRange(-1e12, 1e12)
            value.setDecimals(8)
            value.setValue(default)
            value.valueChanged.connect(self.calibration_changed)
            self.values[key] = value
            column.addWidget(value)
            ref_label = QLabel("未指定")
            self.reference_labels[key] = ref_label
            column.addWidget(ref_label)
            references_layout.addLayout(column)
        layout.addLayout(references_layout)
        labels = QHBoxLayout()
        labels.addWidget(QLabel("x軸名・単位"))
        labels.addWidget(self.x_label)
        labels.addWidget(QLabel("y軸名・単位"))
        labels.addWidget(self.y_label)
        layout.addLayout(labels)
        self.x_label.textChanged.connect(self.refresh)
        self.y_label.textChanged.connect(self.refresh)
        layout.addWidget(QLabel("px：元画像の画素の位置。%：元の試料長に対する変形量の百分率。MPa：応力、1 MPa = 10⁶ N/m²。"))
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.view)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.plot, 2)
        right_layout.addWidget(self.table, 1)
        splitter.addWidget(right)
        splitter.setSizes([850, 550])
        layout.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self.view.clicked.connect(self.on_image_click)
        self.refresh()

    def calibration(self):
        """Input: current GUI references and axis values. Output: validated Calibration."""
        calibration = Calibration(dict(self.references), {k: v.value() for k, v in self.values.items()})
        calibration.validate()
        return calibration

    def confirm_discard(self):
        """Input: unsaved state. Output: bool indicating whether discarding is allowed."""
        if not self.dirty:
            return True
        return QMessageBox.question(self, "未保存のデータ", "未保存のデータを破棄するか。",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "グラフ画像を開く", "", "画像 (*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG)")
        if path:
            self.load_image(path)

    def load_image(self, path):
        """Input: PNG/JPEG path. Output: bool; successful load resets references and data."""
        reader = QImageReader(str(path))
        # Do not apply EXIF rotation: clicks refer to the decoded source raster.
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "画像読込エラー", reader.errorString())
            return False
        if not self.confirm_discard():
            return False
        self.references.clear()
        self.points.clear()
        self.image_path = Path(path)
        self.view.set_image(QPixmap.fromImage(image))
        self.mode.setCurrentIndex(1)
        self.dirty = False
        self.refresh()
        return True

    def on_image_click(self, u, v):
        """Input: source image u/v in px. Output: None; set reference or add data point."""
        mode = self.mode.currentData()
        if mode == "curve":
            try:
                self.calibration()
            except ValueError as error:
                QMessageBox.warning(self, "軸の指定を確認", str(error))
                return
            self.points.append((u, v))
            self.dirty = True
        else:
            self.references[mode] = (u, v)
            self.dirty = bool(self.points) or self.dirty
            # Advance to next reference, then enter curve mode.
            self.mode.setCurrentIndex((self.mode.currentIndex()+1) % self.mode.count())
        self.refresh()

    def calibration_changed(self):
        self.dirty = bool(self.points) or self.dirty
        self.refresh()

    def refresh(self):
        """Input: current references and px points. Output: None; update table and plot."""
        for key, label in self.reference_labels.items():
            label.setText("未指定" if key not in self.references else
                          "u={:.2f} px, v={:.2f} px".format(*self.references[key]))
        self.view.set_markers(self.references, self.points)
        try:
            frame = make_frame(self.points, self.calibration())
            status = f"校正済み | データ点：{len(self.points)} 点"
        except ValueError as error:
            frame = None
            status = str(error)
        self.table.setHorizontalHeaderLabels(["u [px]", "v [px]", self.x_label.text(), self.y_label.text()])
        self.table.setRowCount(len(self.points))
        for row, (u, v) in enumerate(self.points):
            values = [u, v] + (list(frame.iloc[row]) if frame is not None else [None, None])
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem("—" if value is None else f"{value:.10g}"))
        self.plot.update_plot(frame, self.x_label.text(), self.y_label.text())
        self.statusBar().showMessage(status)

    def remove_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.points):
            self.points.pop(row)
            self.dirty = True
            self.refresh()

    def undo(self):
        if self.points:
            self.points.pop()
            self.dirty = True
            self.refresh()

    def export(self):
        try:
            calibration = self.calibration()
            if not self.points:
                raise ValueError("曲線のデータ点を取得する必要がある。")
        except ValueError as error:
            QMessageBox.warning(self, "保存できない", str(error))
            return
        path, _ = QFileDialog.getSaveFileName(self, "CSV保存", str(self.image_path.with_suffix(".csv")), "CSV (*.csv)")
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
            if Path(path).exists() and QMessageBox.question(self, "上書き確認", "既存CSVを上書きするか。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                return
        try:
            save_csv(path, self.points, calibration)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "CSV保存エラー", str(error))
            return
        self.dirty = False
        self.statusBar().showMessage(f"CSVを保存した：{path}")

    def closeEvent(self, event):
        if self.confirm_discard():
            event.accept()
        else:
            event.ignore()


def main():
    """Input: process argv. Output: Qt event-loop exit code (integer, unitless)."""
    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()
