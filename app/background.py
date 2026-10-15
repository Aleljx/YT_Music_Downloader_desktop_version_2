"""
Фон для «Красивой темы»: глубокий чёрный + полупрозрачные размытые цветовые пятна.

Пятна — это радиальные градиенты с плавным затуханием прозрачности (получается
мягкое «размытие» без настоящего blur-эффекта, поэтому это дёшево по ресурсам).
Их цвета строятся от выбранного акцентного цвета: он сам и соседние оттенки.
Готовая картинка кэшируется и перерисовывается только при смене размера или цвета.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget

DEEP_BLACK = QColor("#000000")

# (x, y, радиус как доля большей стороны, сдвиг оттенка в градусах, осветление, непрозрачность 0..1)
_BLOBS = (
    (0.14, 0.18, 0.55, 0, 1.00, 0.70),
    (0.88, 0.12, 0.45, 38, 1.05, 0.55),
    (0.78, 0.88, 0.60, -35, 1.00, 0.62),
    (0.12, 0.86, 0.42, 70, 1.10, 0.32),
    (0.52, 0.48, 0.34, -15, 0.90, 0.22),
)


def _shifted(base: QColor, hue_shift: int, lightness: float) -> QColor:
    h, s, l, _a = base.getHslF()
    h = ((h * 360 + hue_shift) % 360) / 360
    color = QColor()
    color.setHslF(h, min(1.0, max(s, 0.55)), min(0.7, max(0.35, l * lightness)), 1.0)
    return color


class BlobBackground(QWidget):
    """Центральный виджет окна. Если «красивая тема» выключена — ведёт себя как обычный
    виджет (фон берётся из QSS), если включена — рисует чёрный фон с цветными пятнами."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._active = False
        self._accent = QColor("#378ADD")
        self._cache: QPixmap | None = None
        self._cache_key: tuple | None = None

    def configure(self, active: bool, accent: str) -> None:
        self._active = active
        self._accent = QColor(accent)
        self._cache = None
        self.update()

    def _render(self) -> QPixmap:
        dpr = self.devicePixelRatioF()
        pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(DEEP_BLACK)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        size = max(w, h)
        for x, y, radius, hue, light, alpha in _BLOBS:
            color = _shifted(self._accent, hue, light)
            grad = QRadialGradient(x * w, y * h, radius * size)
            c0, c1, c2 = QColor(color), QColor(color), QColor(color)
            c0.setAlphaF(alpha)
            c1.setAlphaF(alpha * 0.35)
            c2.setAlphaF(0.0)
            grad.setColorAt(0.0, c0)
            grad.setColorAt(0.5, c1)
            grad.setColorAt(1.0, c2)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(grad)
            painter.drawRect(0, 0, w, h)
        painter.end()
        return pm

    def paintEvent(self, event) -> None:
        if not self._active:
            super().paintEvent(event)
            return
        key = (self.width(), self.height(), self._accent.name(), self.devicePixelRatioF())
        if self._cache is None or self._cache_key != key:
            self._cache = self._render()
            self._cache_key = key
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)
        painter.end()