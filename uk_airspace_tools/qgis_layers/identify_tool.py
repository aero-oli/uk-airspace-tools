from __future__ import annotations


try:
    from qgis.gui import QgsMapToolIdentify
except ImportError:  # pragma: no cover - QGIS-only map tool.
    QgsMapToolIdentify = None


class AirspaceIdentifyTool(QgsMapToolIdentify if QgsMapToolIdentify else object):
    def __init__(self, canvas, layer_provider, callback):
        if QgsMapToolIdentify is None:
            raise RuntimeError("PyQGIS is required to inspect airspace from the map canvas.")
        super().__init__(canvas)
        self.canvas = canvas
        self.layer_provider = layer_provider
        self.callback = callback

    def canvasReleaseEvent(self, event):  # noqa: N802 - PyQGIS API name.
        layers = [layer for layer in self.layer_provider() if layer is not None]
        if not layers:
            self.callback([])
            return
        self.callback(self.toMapCoordinates(event.pos()))
