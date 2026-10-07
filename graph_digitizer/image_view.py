"""Image display with scene coordinates fixed to original image pixels."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem


class ImageView(QGraphicsView):
    clicked = Signal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.image_item = None
        self.markers = []

    def set_image(self, pixmap: QPixmap):
        """Input: image pixmap. Output: None; scene uses one unit per source pixel."""
        self.scene().clear()
        self.markers.clear()
        self.image_item = self.scene().addPixmap(pixmap)
        self.scene().setSceneRect(self.image_item.boundingRect())
        self.fit_image()

    def fit_image(self):
        """Input: current scene. Output: None; fit the image inside the view."""
        if self.image_item is not None:
            self.fitInView(self.image_item, Qt.AspectRatioMode.KeepAspectRatio)

    def set_markers(self, references, points):
        """Input: reference dict and curve px points. Output: None; replace visible markers."""
        for item in self.markers:
            self.scene().removeItem(item)
        self.markers.clear()
        for label, (u, v), color in [
            *((k, p, "#ff9c00") for k, p in references.items()),
            *((str(i+1), p, "#d500e6") for i, p in enumerate(points)),
        ]:
            marker = self.scene().addEllipse(-4, -4, 8, 8, QPen(QColor(color), 1), QColor(color))
            marker.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            marker.setPos(u, v)
            text = self.scene().addSimpleText(label)
            text.setBrush(QColor(color))
            text.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            text.setPos(u+5, v+5)
            self.markers.extend([marker, text])

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_item is not None:
            pos = self.mapToScene(event.position().toPoint())
            if self.image_item.boundingRect().contains(pos):
                self.clicked.emit(pos.x(), pos.y())
                event.accept()
                return
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        if self.image_item is not None:
            factor = 1.2 if event.angleDelta().y() > 0 else 1/1.2
            scale = self.transform().m11() * factor
            if 0.01 <= scale <= 100:
                self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)
