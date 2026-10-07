"""Matplotlib preview embedded in Qt."""
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class PlotView(FigureCanvasQTAgg):
    def __init__(self):
        self.figure = Figure(figsize=(5, 4), tight_layout=True)
        super().__init__(self.figure)
        self.axes = self.figure.add_subplot(111)

    def update_plot(self, frame, x_label, y_label):
        """Input: x/y frame and axis labels with units. Output: None; redraw plot."""
        self.axes.clear()
        if frame is not None and not frame.empty:
            self.axes.plot(frame["x"], frame["y"], "o-", markersize=4)
        self.axes.set_xlabel(x_label)
        self.axes.set_ylabel(y_label)
        self.axes.grid(True)
        self.draw_idle()

    def compare(self, curves, x_label, y_label, show_points=False):
        """Input: (filename, x/y frame) pairs, labels, marker switch. Output: redraw; None."""
        self.axes.clear()
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
