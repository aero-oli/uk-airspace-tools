from __future__ import annotations


try:
    from qgis.PyQt.QtCore import QRectF, Qt
    from qgis.PyQt.QtGui import QColor, QFont, QPainter, QPen
    from qgis.PyQt.QtWidgets import QDialog, QToolTip, QVBoxLayout, QWidget
except ImportError:  # pragma: no cover - QGIS-only UI module.
    QDialog = None
    QWidget = object


class AirspaceCrossSectionDialog(QDialog if QDialog else object):
    def __init__(self, bands: list[dict], parent=None, band_clicked_callback=None):
        if QDialog is None:
            raise RuntimeError("PyQGIS/PyQt is required to show the cross-section diagram.")
        super().__init__(parent)
        self.setWindowTitle("Airspace Cross-section")
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(AirspaceCrossSectionWidget(bands, self, band_clicked_callback=band_clicked_callback))


class AirspaceCrossSectionWidget(QWidget):
    def __init__(self, bands: list[dict], parent=None, band_clicked_callback=None):
        super().__init__(parent)
        self.bands = bands
        self._hit_regions = []
        self.band_clicked_callback = band_clicked_callback
        self.setMouseTracking(True)
        self.setMinimumSize(720, 460)

    def paintEvent(self, _event):  # noqa: N802 - Qt API name.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(248, 249, 250))
        self._hit_regions = []

        if not self.bands:
            painter.drawText(self.rect(), Qt.AlignCenter, "No airspace at clicked point")
            return

        margin_left = 82
        margin_right = 26
        margin_top = 42
        margin_bottom = 44
        chart = self.rect().adjusted(margin_left, margin_top, -margin_right, -margin_bottom)
        max_altitude = max(1000, max((band["upper_ft"] or 0) for band in self.bands))
        max_altitude = min(max_altitude, 66000)

        self._draw_title(painter)
        self._draw_axis(painter, chart, max_altitude)

        band_count = len(self.bands)
        lane_width = max(58, min(96, int(chart.width() / max(band_count, 1))))
        for index, band in enumerate(self.bands):
            x = chart.left() + index * lane_width
            if x + lane_width > chart.right():
                x = chart.right() - lane_width
            self._draw_band(painter, chart, max_altitude, x, lane_width - 8, band)

        painter.end()

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API name.
        for rect, band in self._hit_regions:
            if rect.contains(event.pos()):
                QToolTip.showText(event.globalPos(), band.get("tooltip", band.get("label", "")), self)
                return
        QToolTip.hideText()

    def mousePressEvent(self, event):  # noqa: N802 - Qt API name.
        if self.band_clicked_callback is None:
            return
        for rect, band in self._hit_regions:
            if rect.contains(event.pos()):
                self.band_clicked_callback(band)
                return

    def _draw_title(self, painter):
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.setPen(QPen(QColor(20, 20, 20)))
        painter.drawText(14, 24, f"{len(self.bands)} airspace features at clicked point - click a block to isolate it")

    def _draw_axis(self, painter, chart, max_altitude):
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(chart.left(), chart.top(), chart.left(), chart.bottom())
        painter.drawLine(chart.left(), chart.bottom(), chart.right(), chart.bottom())

        tick_values = self._tick_values(max_altitude)
        small_font = QFont()
        small_font.setPointSize(8)
        painter.setFont(small_font)
        for value in tick_values:
            y = self._altitude_to_y(chart, max_altitude, value)
            painter.setPen(QPen(QColor(210, 214, 220), 1))
            painter.drawLine(chart.left(), y, chart.right(), y)
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawLine(chart.left() - 5, y, chart.left(), y)
            painter.drawText(8, y + 4, self._altitude_label(value))

    def _draw_band(self, painter, chart, max_altitude, x, width, band):
        lower = max(0, band["lower_ft"] or 0)
        upper = band["upper_ft"]
        open_top = upper is None
        if upper is None:
            upper = max_altitude
        upper = min(max_altitude, max(upper, lower + 50))

        y_top = self._altitude_to_y(chart, max_altitude, upper)
        y_bottom = self._altitude_to_y(chart, max_altitude, lower)
        height = max(18, y_bottom - y_top)
        rect = QRectF(x, y_top, width, height)

        fill = QColor(band["color"])
        fill.setAlpha(105)
        outline = QColor(band["color"])
        painter.setPen(QPen(outline, 1.4))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, 3, 3)
        self._hit_regions.append((rect, band))

        if open_top:
            painter.setPen(QPen(outline, 1, Qt.DashLine))
            painter.drawLine(int(rect.left()), int(rect.top()), int(rect.right()), int(rect.top()))

        label_font = QFont()
        label_font.setPointSize(8)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QPen(QColor(20, 20, 20)))
        painter.drawText(
            rect.adjusted(4, 2, -4, -2),
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            band["short_label"],
        )

        limit_font = QFont()
        limit_font.setPointSize(7)
        painter.setFont(limit_font)
        painter.setPen(QPen(QColor(45, 45, 45)))
        painter.drawText(int(rect.left()), int(rect.bottom()) + 12, band["lower_label"])
        painter.drawText(int(rect.left()), max(12, int(rect.top()) - 4), band["upper_label"])

    @staticmethod
    def _altitude_to_y(chart, max_altitude: float, altitude: float) -> int:
        ratio = max(0.0, min(1.0, altitude / max(max_altitude, 1)))
        return int(chart.bottom() - ratio * chart.height())

    @staticmethod
    def _tick_values(max_altitude: float) -> list[int]:
        if max_altitude <= 5000:
            step = 1000
        elif max_altitude <= 15000:
            step = 2500
        else:
            step = 5000
        values = list(range(0, int(max_altitude) + step, step))
        if values[-1] != int(max_altitude):
            values.append(int(max_altitude))
        return values

    @staticmethod
    def _altitude_label(value: int) -> str:
        if value >= 10000 and value % 100 == 0:
            return f"FL{int(value / 100):03d}"
        return f"{value:,} ft"
