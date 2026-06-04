from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from ..storage.schema import LAYER_NAMES
from ..storage.static_schema import STATIC_LAYER_NAMES
from .styles import apply_notam_map_tip, apply_notam_style, apply_static_airspace_map_tip, apply_static_airspace_style


class LayerManager:
    GROUP_NAME = "UK Airspace"
    STATIC_GROUP_NAME = "UK Permanent Airspace"

    def __init__(self, iface, warning_handler=None):
        self.iface = iface
        self.warning_handler = warning_handler

    def load_cache_layers(self, gpkg_path: str | Path) -> dict[str, object]:
        try:
            from qgis.core import QgsProject, QgsVectorLayer
        except ImportError as exc:
            raise RuntimeError("PyQGIS is required to load layers into the QGIS project.") from exc

        gpkg_path = Path(gpkg_path)
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        group = root.findGroup(self.GROUP_NAME)
        if group is None:
            group = root.addGroup(self.GROUP_NAME)
        else:
            self._remove_group_layers(project, group)

        layers = {}
        definitions = [
            ("polygon", LAYER_NAMES["polygon"], "NOTAM polygons"),
            ("point", LAYER_NAMES["point"], "NOTAM points"),
            ("text_only", LAYER_NAMES["text_only"], "NOTAM text-only"),
        ]
        for key, layer_name, display_name in definitions:
            uri = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, display_name, "ogr")
            if not layer.isValid():
                raise RuntimeError(f"Could not load layer '{layer_name}' from {gpkg_path}")
            project.addMapLayer(layer, False)
            group.addLayer(layer)
            if key == "polygon":
                apply_notam_style(layer, "polygon")
            elif key == "point":
                apply_notam_style(layer, "point")
            apply_notam_map_tip(layer)
            layers[key] = layer

        self.apply_filters(layers)
        self.iface.mapCanvas().refresh()
        return layers

    def load_static_airspace_layers(self, gpkg_path: str | Path) -> dict[str, object]:
        try:
            from qgis.core import QgsProject, QgsVectorLayer
        except ImportError as exc:
            raise RuntimeError("PyQGIS is required to load permanent airspace layers into the QGIS project.") from exc

        gpkg_path = Path(gpkg_path)
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        group = root.findGroup(self.STATIC_GROUP_NAME)
        if group is None:
            group = root.addGroup(self.STATIC_GROUP_NAME)
        else:
            self._remove_group_layers(project, group)

        definitions = [
            ("controlled", STATIC_LAYER_NAMES["controlled"], "Controlled airspace", "Controlled airspace"),
            ("aerodrome", STATIC_LAYER_NAMES["aerodrome"], "Aerodrome zones", "Aerodrome zones"),
            ("restrictions", STATIC_LAYER_NAMES["restrictions"], "Airspace restrictions", "Airspace restrictions"),
            ("radio", STATIC_LAYER_NAMES["radio"], "Radio/transponder zones", "Radio/transponder zones"),
            ("routes", STATIC_LAYER_NAMES["routes"], "Airways/routes", "Airways/routes"),
            ("other", STATIC_LAYER_NAMES["other"], "Other permanent airspace", "Other permanent airspace"),
            ("text_only", STATIC_LAYER_NAMES["text_only"], "Permanent airspace records without geometry", None),
        ]
        layers = {}
        for key, layer_name, display_name, category in definitions:
            uri = f"{gpkg_path}|layername={layer_name}"
            layer = QgsVectorLayer(uri, display_name, "ogr")
            if not layer.isValid():
                raise RuntimeError(f"Could not load layer '{layer_name}' from {gpkg_path}")
            project.addMapLayer(layer, False)
            group.addLayer(layer)
            if category:
                apply_static_airspace_style(layer, category)
            apply_static_airspace_map_tip(layer)
            layers[key] = layer

        self.apply_static_airspace_filters(layers)
        self.iface.mapCanvas().refresh()
        return layers

    def apply_filters(
        self,
        layers: dict[str, object],
        time_filter: str = "active_now",
        custom_start_date: str = "",
        custom_end_date: str = "",
        status_filter: str = "operational",
        activity_filter: str = "all",
        fir_filter: str = "all",
        scope_filter: str = "all",
        qcode_filter: str = "all",
        radius_filter: str = "up_to_100",
        altitude_filter: str = "all",
        custom_min_altitude_ft: str = "",
        custom_max_altitude_ft: str = "",
        keyword: str = "",
        show_polygons: bool = True,
        show_points: bool = True,
        show_text_only: bool = True,
        show_expired: bool = False,
    ) -> None:
        subset = self._subset_expression(
            time_filter=time_filter,
            custom_start_date=custom_start_date,
            custom_end_date=custom_end_date,
            status_filter=status_filter,
            activity_filter=activity_filter,
            fir_filter=fir_filter,
            scope_filter=scope_filter,
            qcode_filter=qcode_filter,
            radius_filter=radius_filter,
            altitude_filter=altitude_filter,
            custom_min_altitude_ft=custom_min_altitude_ft,
            custom_max_altitude_ft=custom_max_altitude_ft,
            keyword=keyword,
            show_expired=show_expired,
        )
        for layer in layers.values():
            self._apply_subset(layer, subset, "NOTAM")

        self._set_visible(layers.get("polygon"), show_polygons)
        self._set_visible(layers.get("point"), show_points)
        self._set_visible(layers.get("text_only"), show_text_only)

    def clear_group(self) -> None:
        try:
            from qgis.core import QgsProject
        except ImportError:
            return
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.GROUP_NAME)
        if group:
            self._remove_group_layers(QgsProject.instance(), group)

    def clear_static_group(self) -> None:
        try:
            from qgis.core import QgsProject
        except ImportError:
            return
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(self.STATIC_GROUP_NAME)
        if group:
            self._remove_group_layers(QgsProject.instance(), group)

    def zoom_to_active(self, layers: dict[str, object]) -> None:
        extent = None
        for key in ("polygon", "point"):
            layer = layers.get(key)
            if not layer:
                continue
            try:
                layer.updateExtents()
            except Exception:
                self._warn(f"Could not update extent for layer '{self._layer_name(layer)}'.")
            layer_extent = layer.extent()
            if layer_extent and not layer_extent.isEmpty():
                if extent is None:
                    extent = layer_extent
                else:
                    extent.combineExtentWith(layer_extent)
        if extent is not None:
            self.iface.mapCanvas().setExtent(extent)
            self.iface.mapCanvas().refresh()

    def apply_static_airspace_filters(
        self,
        layers: dict[str, object],
        static_category_filter: str = "all",
        static_type_filter: str = "all",
        altitude_filter: str = "all",
        custom_min_altitude_ft: str = "",
        custom_max_altitude_ft: str = "",
        keyword: str = "",
        show_permanent_airspace: bool = True,
    ) -> None:
        subset = self._static_subset_expression(
            static_category_filter=static_category_filter,
            static_type_filter=static_type_filter,
            altitude_filter=altitude_filter,
            custom_min_altitude_ft=custom_min_altitude_ft,
            custom_max_altitude_ft=custom_max_altitude_ft,
            keyword=keyword,
        )
        for layer in layers.values():
            self._apply_subset(layer, subset, "permanent airspace")
            self._set_visible(layer, show_permanent_airspace)

    @staticmethod
    def _subset_expression(
        time_filter: str,
        custom_start_date: str,
        custom_end_date: str,
        status_filter: str,
        activity_filter: str,
        fir_filter: str,
        scope_filter: str,
        qcode_filter: str,
        radius_filter: str,
        altitude_filter: str,
        custom_min_altitude_ft: str,
        custom_max_altitude_ft: str,
        keyword: str,
        show_expired: bool,
    ) -> str:
        now = datetime.now(timezone.utc)
        clauses = []
        if time_filter == "active_now":
            clauses.append(f"(effective_start IS NULL OR effective_start <= '{now.isoformat()}')")
            clauses.append(f"(effective_end IS NULL OR effective_end >= '{now.isoformat()}')")
        elif time_filter == "next_24_hours":
            end = now + timedelta(hours=24)
            clauses.append(f"(effective_start IS NULL OR effective_start <= '{end.isoformat()}')")
            clauses.append(f"(effective_end IS NULL OR effective_end >= '{now.isoformat()}')")
        elif time_filter == "next_7_days":
            end = now + timedelta(days=7)
            clauses.append(f"(effective_start IS NULL OR effective_start <= '{end.isoformat()}')")
            clauses.append(f"(effective_end IS NULL OR effective_end >= '{now.isoformat()}')")
        else:
            window = LayerManager._date_window(time_filter, custom_start_date, custom_end_date, now)
            if window:
                start, end = window
                clauses.append(LayerManager._validity_overlap_expression(start, end))

        if status_filter == "operational":
            clauses.append("(status IS NULL OR status NOT IN ('cancelled', 'expired'))")
        elif status_filter != "all":
            clauses.append(f"status = '{LayerManager._escape_literal(status_filter)}'")
        elif not show_expired:
            clauses.append("(status <> 'expired' OR status IS NULL)")

        if radius_filter == "up_to_25":
            clauses.append("(radius_nm IS NULL OR radius_nm <= 25)")
        elif radius_filter == "up_to_100":
            clauses.append("(radius_nm IS NULL OR radius_nm <= 100)")
        elif radius_filter == "large_only":
            clauses.append("radius_nm > 100")

        altitude_range = LayerManager._altitude_range(
            altitude_filter,
            custom_min_altitude_ft,
            custom_max_altitude_ft,
        )
        if altitude_range:
            min_altitude, max_altitude = altitude_range
            clauses.append(LayerManager._vertical_overlap_expression(min_altitude, max_altitude))

        for field_name, value in [
            ("activity_group", activity_filter),
            ("fir", fir_filter),
            ("scope", scope_filter),
        ]:
            if value and value != "all":
                clauses.append(f"{field_name} = '{LayerManager._escape_literal(value)}'")

        if qcode_filter and qcode_filter != "all":
            clauses.append(f"qcode LIKE '{LayerManager._escape_literal(qcode_filter)}%'")

        keyword = keyword.strip().replace("'", "''")
        if keyword:
            keyword_fields = [
                "id",
                "source_id",
                "qcode",
                "icao_location",
                "fir",
                "activity_group",
                "description",
                "raw_text",
            ]
            clauses.append(
                "(" + " OR ".join(f"{field_name} LIKE '%{keyword}%'" for field_name in keyword_fields) + ")"
            )

        return " AND ".join(clauses)

    @staticmethod
    def _escape_literal(value: str) -> str:
        return str(value).replace("'", "''")

    @staticmethod
    def _static_subset_expression(
        static_category_filter: str,
        static_type_filter: str,
        altitude_filter: str,
        custom_min_altitude_ft: str,
        custom_max_altitude_ft: str,
        keyword: str,
    ) -> str:
        clauses = []
        if static_category_filter and static_category_filter != "all":
            clauses.append(f"category = '{LayerManager._escape_literal(static_category_filter)}'")
        if static_type_filter and static_type_filter != "all":
            clauses.append(f"airspace_type = '{LayerManager._escape_literal(static_type_filter)}'")
        altitude_range = LayerManager._altitude_range(
            altitude_filter,
            custom_min_altitude_ft,
            custom_max_altitude_ft,
        )
        if altitude_range:
            min_altitude, max_altitude = altitude_range
            clauses.append(LayerManager._vertical_overlap_expression(min_altitude, max_altitude))
        keyword = keyword.strip().replace("'", "''")
        if keyword:
            clauses.append(
                "("
                + " OR ".join(
                    f"{field_name} LIKE '%{keyword}%'"
                    for field_name in ["id", "name", "designator", "airspace_type", "category", "remarks"]
                )
                + ")"
            )
        return " AND ".join(clauses)

    @staticmethod
    def _altitude_range(
        altitude_filter: str,
        custom_min_altitude_ft: str,
        custom_max_altitude_ft: str,
    ) -> tuple[float | None, float | None] | None:
        ranges = {
            "sfc_1000": (0.0, 1000.0),
            "sfc_5000": (0.0, 5000.0),
            "sfc_fl100": (0.0, 10000.0),
            "fl100_fl200": (10000.0, 20000.0),
            "above_fl200": (20000.0, None),
        }
        if altitude_filter in ranges:
            return ranges[altitude_filter]
        if altitude_filter != "custom":
            return None

        min_altitude = LayerManager._parse_altitude(custom_min_altitude_ft)
        max_altitude = LayerManager._parse_altitude(custom_max_altitude_ft)
        if min_altitude is None and max_altitude is None:
            return None
        return min_altitude, max_altitude

    @staticmethod
    def _parse_altitude(value: str) -> float | None:
        value = (value or "").strip().upper().replace(",", "")
        if not value:
            return None
        if value.startswith("FL"):
            value = value[2:].strip()
            try:
                return float(value) * 100
            except ValueError:
                return None
        if value.endswith("FT"):
            value = value[:-2].strip()
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _vertical_overlap_expression(min_altitude: float | None, max_altitude: float | None) -> str:
        clauses = []
        if max_altitude is not None:
            clauses.append(f"(lower_altitude_ft IS NULL OR lower_altitude_ft <= {max_altitude:g})")
        if min_altitude is not None:
            clauses.append(f"(upper_altitude_ft IS NULL OR upper_altitude_ft >= {min_altitude:g})")
        return "(" + " AND ".join(clauses) + ")"

    @staticmethod
    def _date_window(
        time_filter: str,
        custom_start_date: str,
        custom_end_date: str,
        now: datetime,
    ) -> tuple[datetime, datetime] | None:
        today = now.date()
        if time_filter == "today":
            return LayerManager._whole_day_window(today)
        if time_filter == "tomorrow":
            return LayerManager._whole_day_window(today + timedelta(days=1))
        if time_filter == "this_week":
            start = today - timedelta(days=today.weekday())
            return LayerManager._date_range_window(start, start + timedelta(days=6))
        if time_filter == "this_weekend":
            start = today + timedelta(days=(5 - today.weekday()) % 7)
            return LayerManager._date_range_window(start, start + timedelta(days=1))
        if time_filter == "custom_dates":
            start = LayerManager._parse_date(custom_start_date)
            end = LayerManager._parse_date(custom_end_date)
            if start is None and end is None:
                return None
            start = start or end
            end = end or start
            if end < start:
                start, end = end, start
            return LayerManager._date_range_window(start, end)
        return None

    @staticmethod
    def _whole_day_window(day: date) -> tuple[datetime, datetime]:
        return LayerManager._date_range_window(day, day)

    @staticmethod
    def _date_range_window(start: date, end: date) -> tuple[datetime, datetime]:
        return (
            datetime.combine(start, time.min, tzinfo=timezone.utc),
            datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc),
        )

    @staticmethod
    def _parse_date(value: str) -> date | None:
        try:
            return date.fromisoformat((value or "").strip())
        except ValueError:
            return None

    @staticmethod
    def _validity_overlap_expression(start: datetime, end: datetime) -> str:
        return (
            f"(effective_start IS NULL OR effective_start < '{end.isoformat()}') "
            f"AND (effective_end IS NULL OR effective_end >= '{start.isoformat()}')"
        )

    def _set_visible(self, layer, visible: bool) -> None:
        if not layer:
            return
        try:
            from qgis.core import QgsProject
        except ImportError:
            return
        tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
        if tree_layer:
            tree_layer.setItemVisibilityChecked(visible)

    def _apply_subset(self, layer, subset: str, label: str) -> None:
        try:
            layer.setSubsetString(subset)
            layer.updateExtents()
            layer.triggerRepaint()
        except Exception as exc:
            self._warn(
                f"Could not apply {label} filter to layer '{self._layer_name(layer)}': {exc}. "
                f"Subset expression: {subset or '<none>'}"
            )

    def _warn(self, message: str) -> None:
        if self.warning_handler:
            self.warning_handler(message)

    @staticmethod
    def _layer_name(layer) -> str:
        try:
            return layer.name()
        except Exception:
            return "unknown"

    @staticmethod
    def _remove_group_layers(project, group) -> None:
        for layer_node in list(group.findLayers()):
            try:
                project.removeMapLayer(layer_node.layerId())
            except Exception:
                pass
        group.removeAllChildren()
