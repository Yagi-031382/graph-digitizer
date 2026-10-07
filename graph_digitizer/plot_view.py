"""Matplotlib preview embedded in Qt."""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np


class PlotView(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)
        self.selection_marker = None
        self.frame = None

    def update_plot(self, frame, x_label, y_label, selected_index=None):
        """Input: x/y frame, labels, optional row index. Output: plot with selected point orange; None."""
        self.axes.clear()
        self.frame = frame
        if frame is not None and not frame.empty:
            self.axes.plot(frame["x"], frame["y"], "o-", markersize=4)
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.grid(True)
        self.selection_marker = self.axes.scatter([], [], color="#ff8c00", s=64, zorder=5)
        self.select_point(selected_index)
        self.draw_idle()

    def select_point(self, index):
        """Input: selected frame row index or None. Output: orange marker update; None."""
        if self.selection_marker is None:
            return
        valid = self.frame is not None and index is not None and 0 <= index < len(self.frame)
        self.selection_marker.set_visible(valid)
        if valid:
            point = self.frame.iloc[index]
            self.selection_marker.set_offsets([[point["x"], point["y"]]])
        else:
            self.selection_marker.set_offsets(np.empty((0, 2)))
        self.draw_idle()

    def compare(self, curves, x_label, y_label, show_points=False):
        """Input: (filename, x/y frame) pairs, labels, marker switch. Output: redraw; None."""
        self.axes.clear()
        self.selection_marker = None
        self.frame = None
        from matplotlib import colormaps
        palette = colormaps["tab20"]
        count = len(curves)
        for index, (name, frame) in enumerate(curves):
            color = palette(index % 20) if count <= 20 else colormaps["hsv"](index / count)
            self.axes.plot(frame["x"], frame["y"], label=name, color=color,
                           linestyle="-", marker="o" if show_points else None, markersize=4)
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.grid(True)
        if curves:
            self.axes.legend()
        self.draw_idle()
