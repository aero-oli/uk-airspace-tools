from __future__ import annotations

import gc
import html
from datetime import datetime, timezone
from pathlib import Path

try:
    from qgis.PyQt.QtCore import QSettings, Qt
    from qgis.PyQt.QtGui import QCursor, QIcon
    from qgis.PyQt.QtWidgets import QAction, QFileDialog, QToolTip
    from qgis.core import QgsApplication, QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsMessageLog, QgsProject, QgsRectangle, Qgis
except ImportError:  # pragma: no cover - QGIS-only plugin entrypoint.
    QSettings = None
    QAction = None
    Qt = None
    QCursor = None
    QIcon = None
    QFileDialog = None
    QToolTip = None
    QgsApplication = None
    QgsCoordinateTransform = None
    QgsFeatureRequest = None
    QgsGeometry = None
    QgsMessageLog = None
    QgsProject = None
    QgsRectangle = None
    Qgis = None

from .providers.local_file import LocalFileProvider
from .providers.nats_aip_dataset import NatsAipDatasetProvider
from .providers.nats_pib_xml import DEFAULT_NATS_PIB_URL, NatsPibXmlProvider
from .qgis_layers.identify_tool import AirspaceIdentifyTool
from .qgis_layers.layer_manager import LayerManager
from .tasks import AirspaceRefreshTask
from .ui.cross_section_dialog import AirspaceCrossSectionDialog
from .ui.dock_widget import UkAirspaceDockWidget


class UkAirspaceToolsPlugin:
    MENU_NAME = "UK Airspace Tools"
    CACHE_PREFIX = "uk_airspace_cache"
    STATIC_CACHE_PREFIX = "uk_permanent_airspace_cache"

    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.actions = []
        self.layer_manager = LayerManager(iface, warning_handler=self._warn)
        self.layers = {}
        self.static_layers = {}
        self.last_local_file = None
        self.last_local_aip_file = None
        self.status_stats = {}
        self.identify_tool = None
        self.cross_section_dialog = None
        self.static_isolation = None
        self.active_refresh_task = None
        self.latest_parse_warnings = []

    def initGui(self) -> None:
        self.open_action = self._action("Open UK Airspace Panel")
        self.open_action.triggered.connect(self.open_panel)
        self.refresh_action = self._action("Refresh NOTAMs")
        self.refresh_action.triggered.connect(self.refresh_notams)
        self.refresh_permanent_action = self._action("Refresh Permanent Airspace")
        self.refresh_permanent_action.triggered.connect(self.refresh_permanent_airspace)

        for action in [self.open_action, self.refresh_action, self.refresh_permanent_action]:
            self.iface.addPluginToMenu(self.MENU_NAME, action)
            self.iface.addToolBarIcon(action)
            self.actions.append(action)

    def _action(self, text: str):
        icon = self._plugin_icon()
        if icon is not None:
            return QAction(icon, text, self.iface.mainWindow())
        return QAction(text, self.iface.mainWindow())

    @staticmethod
    def _plugin_icon():
        if QIcon is None:
            return None
        icon_path = Path(__file__).with_name("icon.svg")
        if not icon_path.exists():
            return None
        return QIcon(str(icon_path))

    def unload(self) -> None:
        for action in self.actions:
            self.iface.removePluginMenu(self.MENU_NAME, action)
            self.iface.removeToolBarIcon(action)
        self.actions = []
        if self.dock:
            self.iface.removeDockWidget(self.dock)
            self.dock = None
        if self.active_refresh_task:
            try:
                self.active_refresh_task.cancel()
            except Exception:
                pass
            self.active_refresh_task = None
        self.identify_tool = None
        self.cross_section_dialog = None

    def open_panel(self) -> None:
        if self.dock is None:
            self.dock = UkAirspaceDockWidget(self.iface.mainWindow())
            self.dock.refreshRequested.connect(self.refresh_notams)
            self.dock.permanentRefreshRequested.connect(self.refresh_permanent_airspace)
            self.dock.localFileRequested.connect(self.load_local_file)
            self.dock.localAipFileRequested.connect(self.load_local_aip_file)
            self.dock.clearRequested.connect(self.clear_layers)
            self.dock.clearPermanentRequested.connect(self.clear_permanent_airspace)
            self.dock.clearIsolationRequested.connect(self.clear_static_isolation)
            self.dock.zoomRequested.connect(self.zoom_to_active)
            self.dock.inspectNotamsRequested.connect(self.activate_notam_inspect_mode)
            self.dock.inspectAirspaceRequested.connect(self.activate_airspace_cross_section_mode)
            self.dock.filtersChanged.connect(self.apply_filters)
            self.dock.cancelRefreshRequested.connect(self.cancel_refresh)
            self.dock.warningsRequested.connect(self.show_parse_warnings)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.show()
        self.dock.raise_()

    def refresh_notams(self) -> None:
        self.open_panel()
        try:
            if self.dock.selected_source() == "local":
                if not self.last_local_file:
                    file_path, _ = QFileDialog.getOpenFileName(
                        self.iface.mainWindow(),
                        "Load NOTAM XML File",
                        "",
                        "XML files (*.xml);;All files (*.*)",
                    )
                    if not file_path:
                        return
                    self.last_local_file = file_path
                provider = LocalFileProvider(self.last_local_file)
            else:
                provider = NatsPibXmlProvider(self._configured_url())
            self._start_refresh_task("notam", provider, self._cache_path(), "Refreshing NOTAMs")
        except Exception as exc:
            self._warn(f"Refresh failed: {exc}")

    def load_local_file(self, file_path: str) -> None:
        self.last_local_file = file_path
        try:
            self._start_refresh_task("notam", LocalFileProvider(file_path), self._cache_path(), "Loading local NOTAM XML")
        except Exception as exc:
            self._warn(f"Local XML import failed: {exc}")

    def refresh_permanent_airspace(self) -> None:
        self.open_panel()
        try:
            self._start_refresh_task("static", NatsAipDatasetProvider(), self._static_cache_path(), "Refreshing permanent airspace")
        except Exception as exc:
            self._warn(f"Permanent airspace refresh failed: {exc}")

    def load_local_aip_file(self, file_path: str) -> None:
        self.last_local_aip_file = file_path
        try:
            provider = NatsAipDatasetProvider()
            self._start_refresh_task(
                "static",
                provider,
                self._static_cache_path(),
                "Loading local AIP dataset",
                raw_path=file_path,
            )
        except Exception as exc:
            self._warn(f"Local AIP dataset import failed: {exc}")

    def clear_layers(self) -> None:
        self.layer_manager.clear_group()
        self.layers = {}
        self._update_layer_action_state()

    def clear_permanent_airspace(self) -> None:
        self.layer_manager.clear_static_group()
        self.static_layers = {}
        self.static_isolation = None
        self._update_layer_action_state()

    def clear_static_isolation(self) -> None:
        self.static_isolation = None
        self.apply_filters()
        self._update_layer_action_state()

    def zoom_to_active(self) -> None:
        self.layer_manager.zoom_to_active(self.layers)

    def cancel_refresh(self) -> None:
        if self.active_refresh_task is None:
            return
        try:
            self.active_refresh_task.cancel()
            self._update_status({"refresh_status": "Cancelling refresh"})
            if self.dock:
                self.dock.set_refresh_state(True, "Cancelling refresh")
        except Exception as exc:
            self._warn(f"Could not cancel refresh: {exc}")

    def activate_notam_inspect_mode(self) -> None:
        self.open_panel()
        if not self._notam_inspect_layers():
            self._warn("Load NOTAMs before using NOTAM inspect mode.")
            return
        try:
            self.identify_tool = AirspaceIdentifyTool(
                self.iface.mapCanvas(),
                self._notam_inspect_layers,
                self._show_identified_notams,
            )
            self.iface.mapCanvas().setMapTool(self.identify_tool)
            self._info("NOTAM inspect mode active. Click the map to inspect NOTAMs at that point.")
        except Exception as exc:
            self._warn(f"Could not activate NOTAM inspect mode: {exc}")

    def activate_airspace_cross_section_mode(self) -> None:
        self.open_panel()
        if not self._inspect_layers():
            self._warn("Load permanent airspace before using cross-section inspect mode.")
            return
        try:
            self.identify_tool = AirspaceIdentifyTool(
                self.iface.mapCanvas(),
                self._inspect_layers,
                self._show_identified_features,
            )
            self.iface.mapCanvas().setMapTool(self.identify_tool)
            self._info("Cross-section mode active. Click the map to inspect permanent airspace at that point.")
        except Exception as exc:
            self._warn(f"Could not activate inspect mode: {exc}")

    def apply_filters(self) -> None:
        if not self.dock:
            return
        filters = self.dock.filters()
        if self.layers:
            notam_filter_keys = {
                "time_filter",
                "custom_start_date",
                "custom_end_date",
                "status_filter",
                "activity_filter",
                "fir_filter",
                "scope_filter",
                "qcode_filter",
                "radius_filter",
                "altitude_filter",
                "custom_min_altitude_ft",
                "custom_max_altitude_ft",
                "keyword",
                "show_polygons",
                "show_points",
                "show_text_only",
                "show_expired",
            }
            self.layer_manager.apply_filters(self.layers, **{key: filters[key] for key in notam_filter_keys})
        if self.static_layers:
            self.layer_manager.apply_static_airspace_filters(
                self.static_layers,
                static_category_filter=filters["static_category_filter"],
                static_type_filter=filters["static_type_filter"],
                altitude_filter=filters["static_altitude_filter"],
                custom_min_altitude_ft=filters["static_custom_min_altitude_ft"],
                custom_max_altitude_ft=filters["static_custom_max_altitude_ft"],
                keyword=filters["static_keyword"],
                show_permanent_airspace=filters["show_permanent_airspace"],
            )
            if self.static_isolation:
                self._apply_static_isolation()

    def _start_refresh_task(
        self,
        kind: str,
        provider,
        cache_path: Path,
        description: str,
        raw_path: str | None = None,
    ) -> None:
        if self.active_refresh_task is not None:
            self._warn("A refresh is already running. Wait for it to finish or cancel it from QGIS task manager.")
            return
        task = AirspaceRefreshTask(
            description,
            kind=kind,
            provider=provider,
            cache_path=cache_path,
            raw_path=raw_path,
            finished_callback=self._finish_refresh_task,
        )
        self.active_refresh_task = task
        self.latest_parse_warnings = []
        if self.dock:
            self.dock.set_refresh_state(True, description)
            self.dock.set_warning_action_state(0)
        self._update_status({"refresh_status": description, "source_label": self._provider_label(provider, raw_path)})
        QgsApplication.taskManager().addTask(task)

    def _finish_refresh_task(self, task, result: bool) -> None:
        if task is not self.active_refresh_task:
            return
        self.active_refresh_task = None
        if self.dock:
            self.dock.set_refresh_state(False, "Idle")

        if not result:
            if task.isCanceled():
                self._update_status({"refresh_status": "Refresh cancelled"})
                self._warn(f"{task.description()} cancelled.")
                return
            message = f"{task.description()} failed"
            if task.error:
                message = f"{message}: {task.error}"
            self._update_status({"refresh_status": "Refresh failed"})
            self._warn(message)
            return

        try:
            self._load_completed_refresh(task)
        except Exception as exc:
            self._update_status({"refresh_status": "Layer load failed"})
            self._warn(f"{task.description()} completed, but layer loading failed: {exc}")

    def _load_completed_refresh(self, task) -> None:
        if task.gpkg_path is None:
            raise RuntimeError("Refresh task finished without a GeoPackage path.")

        if task.kind == "static":
            self.clear_permanent_airspace()
            self._release_qgis_file_handles()
            self.static_layers = self.layer_manager.load_static_airspace_layers(task.gpkg_path)
            self._connect_selection_handlers(self.static_layers)
            if self.dock:
                self.dock.set_static_filter_options(self._static_filter_options(task.features))
            self.apply_filters()
            self._cleanup_stale_caches(task.gpkg_path, prefix=self.STATIC_CACHE_PREFIX)
            stats = self._static_stats(task.features)
            noun = "permanent airspace records"
        else:
            self.clear_layers()
            self._release_qgis_file_handles()
            self.layers = self.layer_manager.load_cache_layers(task.gpkg_path)
            self._connect_selection_handlers()
            if self.dock:
                self.dock.set_filter_options(self._filter_options(task.features))
            self.apply_filters()
            self.zoom_to_active()
            self._cleanup_stale_caches(task.gpkg_path)
            stats = self._stats(task.features)
            noun = "NOTAMs"

        warning_count = stats["warning_count"]
        self.latest_parse_warnings = self._warning_records(task.kind, task.features)
        status = {
            **stats,
            "refresh_status": "Refresh complete",
            "source_label": self._metadata_source_label(task.metadata),
        }
        self._update_status(status)
        self._update_layer_action_state()
        if self.dock:
            self.dock.set_warning_action_state(len(self.latest_parse_warnings))
        if warning_count:
            self._info(f"Loaded {len(task.features)} {noun} with {warning_count} parse warnings.")
        else:
            self._info(f"Loaded {len(task.features)} {noun}.")

    def _cache_path(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return self._cache_dir() / f"{self.CACHE_PREFIX}_{timestamp}.gpkg"

    def _static_cache_path(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return self._cache_dir() / f"{self.STATIC_CACHE_PREFIX}_{timestamp}.gpkg"

    def _cache_dir(self) -> Path:
        try:
            project_home = QgsProject.instance().homePath()
            if project_home:
                return Path(project_home)
        except Exception:
            pass
        profile = QgsApplication.qgisSettingsDirPath() if QgsApplication else str(Path.home())
        return Path(profile)

    @staticmethod
    def _release_qgis_file_handles() -> None:
        gc.collect()
        try:
            if QgsApplication:
                QgsApplication.processEvents()
        except Exception:
            pass

    def _cleanup_stale_caches(self, current_path: Path, prefix: str | None = None) -> None:
        current_path = Path(current_path)
        prefix = prefix or self.CACHE_PREFIX
        patterns = [
            f"{prefix}.gpkg",
            f"{prefix}.gpkg-*",
            f"{prefix}_*.gpkg",
            f"{prefix}_*.gpkg-*",
        ]
        for pattern in patterns:
            for path in current_path.parent.glob(pattern):
                if path == current_path or path.name.startswith(f"{current_path.name}-"):
                    continue
                try:
                    path.unlink()
                except OSError:
                    pass

    @staticmethod
    def _stats(features) -> dict:
        return {
            "last_refresh": datetime.now(timezone.utc).isoformat(),
            "notam_count": len(features),
            "polygon_count": sum(1 for feature in features if feature.geometry_quality == "qline_radius"),
            "point_count": sum(1 for feature in features if feature.geometry_quality == "qline_point"),
            "text_only_count": sum(1 for feature in features if feature.geometry_quality == "text_only"),
            "local_regional_count": sum(1 for feature in features if feature.radius_nm is None or feature.radius_nm <= 100),
            "large_area_count": sum(1 for feature in features if feature.radius_nm is not None and feature.radius_nm > 100),
            "activity_group_count": len({feature.activity_group for feature in features if feature.activity_group}),
            "warning_count": sum(len(feature.parse_warnings) for feature in features),
        }

    @staticmethod
    def _static_stats(features) -> dict:
        return {
            "permanent_airspace_count": len(features),
            "permanent_polygon_count": sum(1 for feature in features if feature.geometry_wkt),
            "permanent_text_only_count": sum(1 for feature in features if not feature.geometry_wkt),
            "permanent_category_count": len({feature.category for feature in features if feature.category}),
            "warning_count": sum(len(feature.parse_warnings) for feature in features),
        }

    def _update_status(self, stats: dict) -> None:
        self.status_stats.update(stats)
        if self.dock:
            self.dock.set_status(self.status_stats)

    def _update_layer_action_state(self) -> None:
        if not self.dock:
            return
        self.dock.set_layer_action_state(
            has_notams=bool(self.layers),
            has_static_airspace=self._has_inspectable_static_airspace(self.static_layers, self.status_stats),
            isolation_active=bool(self.static_isolation),
        )

    @staticmethod
    def _has_inspectable_static_airspace(static_layers: dict, stats: dict) -> bool:
        polygon_count = stats.get("permanent_polygon_count")
        if polygon_count not in (None, ""):
            try:
                return int(polygon_count) > 0
            except (TypeError, ValueError):
                pass
        return any(key != "text_only" for key in static_layers)

    @staticmethod
    def _provider_label(provider, raw_path: str | None = None) -> str:
        if raw_path:
            return str(raw_path)
        try:
            metadata = provider.source_metadata()
        except Exception:
            metadata = {}
        return UkAirspaceToolsPlugin._metadata_source_label(metadata) or getattr(provider, "display_name", "Unknown source")

    @staticmethod
    def _metadata_source_label(metadata: dict) -> str:
        for key in ("source_file", "file_path", "source_url", "resolved_url", "configured_url", "display_name"):
            value = metadata.get(key)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _warning_records(kind: str, features) -> list[dict]:
        records = []
        for feature in features:
            feature_id = getattr(feature, "id", None) or getattr(feature, "designator", None) or "Unknown feature"
            category = getattr(feature, "activity_group", None) or getattr(feature, "category", None) or ""
            for warning in getattr(feature, "parse_warnings", []):
                records.append(
                    {
                        "kind": kind,
                        "feature_id": feature_id,
                        "category": category,
                        "warning": warning,
                    }
                )
        return records

    def show_parse_warnings(self) -> None:
        if not self.dock:
            return
        if not self.latest_parse_warnings:
            self.dock.set_feature_details("Parse warnings", "No parse warnings are available for the latest refresh.")
            return

        sections = [f"<h3>{len(self.latest_parse_warnings)} parse warning{'s' if len(self.latest_parse_warnings) != 1 else ''}</h3>"]
        for index, record in enumerate(self.latest_parse_warnings, start=1):
            category = f" - {record['category']}" if record["category"] else ""
            sections.append(
                "<p>"
                f"<b>{index}. {html.escape(str(record['feature_id']))}</b>{html.escape(category)}<br/>"
                f"{html.escape(str(record['warning']))}"
                "</p>"
            )
        self.dock.set_feature_details("Parse warnings", "".join(sections), rich=True)

    def _connect_selection_handlers(self, layers=None) -> None:
        for layer in (layers or self.layers).values():
            try:
                layer.selectionChanged.connect(
                    lambda _selected, _deselected, _clear_and_select, selected_layer=layer: self._show_selected_feature(selected_layer)
                )
            except Exception:
                pass

    def _show_selected_feature(self, layer) -> None:
        if not self.dock:
            return
        try:
            selected = layer.selectedFeatures()
        except Exception:
            selected = []
        if not selected:
            self.dock.set_feature_details("No airspace selected", "")
            return
        feature = selected[0]
        count_suffix = f" ({len(selected)} selected)" if len(selected) > 1 else ""
        feature_id = self._feature_value(feature, "id") or self._feature_value(feature, "designator") or "Selected airspace"
        self.dock.set_feature_details(f"{feature_id}{count_suffix}", self._format_feature_details(feature))
        self._show_feature_tooltip(feature, f"{feature_id}{count_suffix}")

    def _show_identified_features(self, map_point) -> None:
        if not self.dock:
            return

        records = self._features_at_map_point(map_point)

        if not records:
            self.dock.set_feature_details(
                "No airspace found",
                "<p>No loaded permanent airspace feature was found at the clicked point.</p>",
                rich=True,
            )
            return

        records.sort(key=self._record_sort_key)
        title = f"{len(records)} airspace feature{'s' if len(records) != 1 else ''} at clicked point"
        self._show_cross_section_dialog(records)
        html_details = self._format_cross_section_html(records)
        self.dock.set_feature_details(title, html_details, rich=True)
        self._show_identify_summary_tooltip(records, title)

    def _show_identified_notams(self, map_point) -> None:
        if not self.dock:
            return
        records = self._features_at_map_point(map_point, layers=self._notam_inspect_layers())
        if not records:
            self.dock.set_feature_details(
                "No NOTAM found",
                "<p>No loaded NOTAM feature was found at the clicked point.</p>",
                rich=True,
            )
            return
        records.sort(key=self._record_sort_key)
        title = f"{len(records)} NOTAM{'s' if len(records) != 1 else ''} at clicked point"
        sections = [f"<h3>{html.escape(title)}</h3>"]
        for index, record in enumerate(records, start=1):
            sections.append(self._feature_summary_block(record, index))
        self.dock.set_feature_details(title, "".join(sections), rich=True)
        self._show_identify_summary_tooltip(records, title)

    def _inspect_layers(self) -> list:
        layers = [layer for key, layer in self.static_layers.items() if key != "text_only"]
        return [layer for layer in layers if self._layer_is_inspectable(layer)]

    def _notam_inspect_layers(self) -> list:
        layers = list(self.layers.values())
        return [layer for layer in layers if self._layer_is_inspectable(layer)]

    def _features_at_map_point(self, map_point, layers=None) -> list[dict]:
        if QgsCoordinateTransform is None or QgsFeatureRequest is None or QgsGeometry is None or QgsRectangle is None:
            return []

        records = []
        canvas_crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        project = QgsProject.instance()
        for layer in (layers or self._inspect_layers()):
            try:
                transform = QgsCoordinateTransform(canvas_crs, layer.crs(), project)
                layer_point = transform.transform(map_point)
                point_geometry = QgsGeometry.fromPointXY(layer_point)
                tolerance = self._map_tolerance_in_layer_units(layer, layer_point)
                search_rect = QgsRectangle(
                    layer_point.x() - tolerance,
                    layer_point.y() - tolerance,
                    layer_point.x() + tolerance,
                    layer_point.y() + tolerance,
                )
                request = QgsFeatureRequest().setFilterRect(search_rect)
                if layer.subsetString():
                    request.setSubsetOfAttributes(layer.fields().names())
                for feature in layer.getFeatures(request):
                    geometry = feature.geometry()
                    if geometry and not geometry.isEmpty() and (geometry.contains(point_geometry) or geometry.intersects(point_geometry)):
                        records.append({"layer": layer, "feature": feature})
            except Exception:
                continue
        return records

    @staticmethod
    def _map_tolerance_in_layer_units(layer, layer_point) -> float:
        try:
            extent = layer.extent()
            width = extent.width()
            height = extent.height()
            if width > 0 and height > 0:
                return max(width, height) / 100000.0
        except Exception:
            pass
        return 0.00001

    @staticmethod
    def _layer_is_inspectable(layer) -> bool:
        try:
            if not layer.isValid():
                return False
        except Exception:
            return False
        try:
            node = QgsProject.instance().layerTreeRoot().findLayer(layer.id())
            if node is not None and hasattr(node, "isVisible"):
                return node.isVisible()
            if node is not None and hasattr(node, "itemVisibilityChecked"):
                return node.itemVisibilityChecked()
        except Exception:
            pass
        return True

    def _record_sort_key(self, record) -> tuple:
        feature = record["feature"]
        lower = self._numeric_feature_value(feature, "lower_altitude_ft")
        upper = self._numeric_feature_value(feature, "upper_altitude_ft")
        lower_sort = lower if lower is not None else 0
        upper_sort = upper if upper is not None else 999999
        return (-upper_sort, lower_sort, self._record_label(record))

    def _format_cross_section_html(self, records: list[dict]) -> str:
        max_altitude = self._cross_section_max_altitude(records)
        sections = [
            "<h3>Vertical cross-section at clicked point</h3>",
            "<p>Features are sorted from highest to lowest. Open or unlimited tops are shown at the top of the diagram.</p>",
            "<table border='1' cellspacing='0' cellpadding='4'>",
            "<tr><th>Vertical slice</th><th>Airspace</th><th>Details</th></tr>",
        ]
        for record in records:
            sections.append(self._cross_section_row(record, max_altitude))
        sections.append("</table>")
        sections.append("<h3>Selected feature details</h3>")
        for index, record in enumerate(records, start=1):
            sections.append(self._feature_summary_block(record, index))
        return "".join(sections)

    def _show_cross_section_dialog(self, records: list[dict]) -> None:
        try:
            bands = [self._diagram_band(record) for record in records]
            self.cross_section_dialog = AirspaceCrossSectionDialog(
                bands,
                self.iface.mainWindow(),
                band_clicked_callback=self._isolate_static_band,
            )
            self.cross_section_dialog.show()
            self.cross_section_dialog.raise_()
        except Exception as exc:
            self._warn(f"Could not draw cross-section diagram: {exc}")

    def _diagram_band(self, record: dict) -> dict:
        feature = record["feature"]
        lower = self._numeric_feature_value(feature, "lower_altitude_ft")
        upper = self._numeric_feature_value(feature, "upper_altitude_ft")
        label = self._record_label(record)
        short_label = label if len(label) <= 22 else label[:19] + "..."
        return {
            "label": label,
            "short_label": short_label,
            "layer_id": record["layer"].id(),
            "feature_id": self._feature_value(feature, "id"),
            "qgis_feature_id": feature.id(),
            "lower_ft": lower,
            "upper_ft": upper,
            "lower_label": self._limit_label(feature, "lower"),
            "upper_label": self._limit_label(feature, "upper"),
            "color": self._record_color(feature),
            "tooltip": self._diagram_tooltip(record),
        }

    def _isolate_static_band(self, band: dict) -> None:
        layer_id = band.get("layer_id")
        feature_id = band.get("feature_id")
        qgis_feature_id = band.get("qgis_feature_id")
        if not layer_id or (feature_id in (None, "") and qgis_feature_id is None):
            self._warn("Could not isolate the selected airspace feature.")
            return
        self.static_isolation = {
            "layer_id": layer_id,
            "feature_id": feature_id,
            "qgis_feature_id": qgis_feature_id,
            "label": band.get("label") or "selected airspace",
        }
        self.apply_filters()
        self._info(f"Isolated {self.static_isolation['label']}. Click 'Show Filtered Airspace' to restore.")

    def _apply_static_isolation(self) -> None:
        if not self.static_isolation:
            return
        target_layer_id = self.static_isolation["layer_id"]
        feature_id = self.static_isolation.get("feature_id")
        qgis_feature_id = self.static_isolation.get("qgis_feature_id")
        for layer in self.static_layers.values():
            try:
                if layer.id() != target_layer_id:
                    layer.setSubsetString("1=0")
                    layer.triggerRepaint()
                    continue
                current_subset = layer.subsetString()
                if feature_id not in (None, ""):
                    id_clause = f"id = '{LayerManager._escape_literal(feature_id)}'"
                else:
                    id_clause = f"$id = {int(qgis_feature_id)}"
                layer.setSubsetString(f"({current_subset}) AND ({id_clause})" if current_subset else id_clause)
                layer.updateExtents()
                layer.triggerRepaint()
            except Exception:
                pass

    def _diagram_tooltip(self, record: dict) -> str:
        feature = record["feature"]
        rows = [
            self._record_label(record),
            "Click this block to show only this feature on the map.",
            "Included because the clicked point is inside this visible permanent-airspace polygon and it passes current Airspace tab filters.",
            f"Layer: {self._layer_name(record['layer'])}",
            f"Type: {self._feature_value(feature, 'airspace_type') or 'unknown'}",
            f"Category: {self._feature_value(feature, 'category') or 'unknown'}",
            f"Class: {self._feature_value(feature, 'airspace_class') or 'unknown'}",
            f"Limits: {self._limit_label(feature, 'lower')} to {self._limit_label(feature, 'upper')}",
        ]
        activation = self._feature_value(feature, "activation_status")
        if activation:
            rows.append(f"Activation: {activation}")
        remarks = self._feature_value(feature, "remarks")
        if remarks:
            summary = " ".join(str(remarks).split())
            rows.append(summary[:350] + ("..." if len(summary) > 350 else ""))
        return "\n".join(str(row) for row in rows if row)

    def _cross_section_row(self, record: dict, max_altitude: float) -> str:
        feature = record["feature"]
        label = html.escape(self._record_label(record))
        layer_name = html.escape(self._layer_name(record["layer"]))
        category = self._feature_value(feature, "category") or self._feature_value(feature, "activity_group") or self._feature_value(feature, "status") or ""
        color = self._record_color(feature)
        lower = self._numeric_feature_value(feature, "lower_altitude_ft")
        upper = self._numeric_feature_value(feature, "upper_altitude_ft")
        lower_label = html.escape(self._limit_label(feature, "lower"))
        upper_label = html.escape(self._limit_label(feature, "upper"))
        bar = self._altitude_bar_html(lower, upper, max_altitude, color)
        details = [
            ("Layer", layer_name),
            ("Type", self._feature_value(feature, "airspace_type") or self._feature_value(feature, "qcode")),
            ("Category", category),
            ("Class", self._feature_value(feature, "airspace_class")),
            ("Activation/status", self._feature_value(feature, "activation_status") or self._feature_value(feature, "status")),
        ]
        detail_text = "<br/>".join(
            f"<b>{html.escape(name)}:</b> {html.escape(str(value))}"
            for name, value in details
            if value not in (None, "")
        )
        return (
            "<tr>"
            f"<td>{upper_label}<br/>{bar}<br/>{lower_label}</td>"
            f"<td><b>{label}</b><br/>{layer_name}</td>"
            f"<td>{detail_text}</td>"
            "</tr>"
        )

    @staticmethod
    def _altitude_bar_html(lower: float | None, upper: float | None, max_altitude: float, color: str) -> str:
        lower_value = 0 if lower is None else max(0, lower)
        upper_value = max_altitude if upper is None else min(max_altitude, max(upper, lower_value))
        height = max(12, int(80 * (upper_value - lower_value) / max(max_altitude, 1)))
        top_space = max(0, int(80 * (max_altitude - upper_value) / max(max_altitude, 1)))
        bottom_space = max(0, 80 - top_space - height)
        return (
            "<div style='width:34px;height:80px;border-left:1px solid #777;border-bottom:1px solid #777;'>"
            f"<div style='height:{top_space}px'></div>"
            f"<div style='height:{height}px;background-color:{color};border:1px solid #333'></div>"
            f"<div style='height:{bottom_space}px'></div>"
            "</div>"
        )

    def _feature_summary_block(self, record: dict, index: int) -> str:
        feature = record["feature"]
        title = html.escape(self._record_label(record))
        details = html.escape(self._format_feature_details(feature)).replace("\n", "<br/>")
        return f"<p><b>{index}. {title}</b><br/>{details}</p>"

    def _cross_section_max_altitude(self, records: list[dict]) -> float:
        values = []
        for record in records:
            upper = self._numeric_feature_value(record["feature"], "upper_altitude_ft")
            lower = self._numeric_feature_value(record["feature"], "lower_altitude_ft")
            if upper is not None:
                values.append(upper)
            if lower is not None:
                values.append(lower)
        if not values:
            return 10000
        return max(1000, min(max(values), 60000))

    def _record_label(self, record: dict) -> str:
        feature = record["feature"]
        return (
            self._feature_value(feature, "name")
            or self._feature_value(feature, "designator")
            or self._feature_value(feature, "id")
            or self._layer_name(record["layer"])
        )

    @staticmethod
    def _layer_name(layer) -> str:
        try:
            return layer.name()
        except Exception:
            return "Layer"

    def _limit_label(self, feature, prefix: str) -> str:
        raw = self._feature_value(feature, f"{prefix}_limit_raw")
        altitude = self._numeric_feature_value(feature, f"{prefix}_altitude_ft")
        if raw:
            return str(raw)
        if altitude is None:
            return "Open" if prefix == "upper" else "Unknown"
        return f"{altitude:g} ft"

    @staticmethod
    def _record_color(feature) -> str:
        category = ""
        try:
            fields = feature.fields()
            for field_name in ("category", "activity_group", "status"):
                index = fields.indexOf(field_name)
                if index >= 0:
                    category = str(feature.attribute(index) or "")
                    break
        except Exception:
            pass
        if "restriction" in category.lower() or category == "cancelled":
            return "#cf4f6f"
        if "controlled" in category.lower():
            return "#4b83d1"
        if "aerodrome" in category.lower() or "obstacle" in category.lower():
            return "#d79532"
        if "radio" in category.lower() or "transponder" in category.lower():
            return "#8c6ad1"
        if "activity" in category.lower() or category == "active":
            return "#d85b50"
        return "#7d8b8c"

    def _numeric_feature_value(self, feature, field_name: str) -> float | None:
        value = self._feature_value(feature, field_name)
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _show_identify_summary_tooltip(self, records: list[dict], title: str) -> None:
        if QToolTip is None or QCursor is None:
            return
        parts = [f"<b>{html.escape(title)}</b>"]
        for record in records[:8]:
            feature = record["feature"]
            label = html.escape(self._record_label(record))
            lower = html.escape(self._limit_label(feature, "lower"))
            upper = html.escape(self._limit_label(feature, "upper"))
            parts.append(f"{label}: {lower} to {upper}")
        if len(records) > 8:
            parts.append(f"...and {len(records) - 8} more")
        QToolTip.showText(
            QCursor.pos(),
            "<br/>".join(parts),
            self.iface.mapCanvas(),
            self.iface.mapCanvas().rect(),
            15000,
        )

    def _format_feature_details(self, feature) -> str:
        rows = [
            ("ID", "id"),
            ("Name", "name"),
            ("Designator", "designator"),
            ("Airspace type", "airspace_type"),
            ("Local type", "local_type"),
            ("Category", "category"),
            ("Class", "airspace_class"),
            ("Status", "status"),
            ("Activation", "activation_status"),
            ("Activity", "activity_group"),
            ("FIR", "fir"),
            ("Location", "icao_location"),
            ("Q-code", "qcode"),
            ("Scope", "scope"),
            ("Traffic", "traffic"),
            ("Effective from", "effective_start"),
            ("Effective to", "effective_end"),
            ("Lower limit", "lower_limit_raw"),
            ("Upper limit", "upper_limit_raw"),
            ("Lower altitude ft", "lower_altitude_ft"),
            ("Upper altitude ft", "upper_altitude_ft"),
            ("Radius NM", "radius_nm"),
            ("Latitude", "latitude"),
            ("Longitude", "longitude"),
            ("Warnings", "parse_warning_count"),
            ("Description", "description"),
            ("Remarks", "remarks"),
        ]
        lines = []
        for label, field_name in rows:
            value = self._feature_value(feature, field_name)
            if value not in (None, ""):
                lines.append(f"{label}: {value}")

        raw_text = self._feature_value(feature, "raw_text")
        if raw_text:
            lines.append("")
            lines.append("Raw NOTAM:")
            lines.append(str(raw_text))
        raw_properties = self._feature_value(feature, "raw_properties")
        if raw_properties:
            lines.append("")
            lines.append("Raw properties:")
            lines.append(str(raw_properties))
        return "\n".join(lines)

    @staticmethod
    def _feature_value(feature, field_name: str):
        try:
            index = feature.fields().indexOf(field_name)
            if index < 0:
                return None
            return feature.attribute(index)
        except Exception:
            return None

    def _show_feature_tooltip(self, feature, title: str) -> None:
        if QToolTip is None or QCursor is None:
            return

        rows = [
            ("Name", "name"),
            ("Type", "airspace_type"),
            ("Category", "category"),
            ("Class", "airspace_class"),
            ("Status", "status"),
            ("Activation", "activation_status"),
            ("Activity", "activity_group"),
            ("FIR", "fir"),
            ("Location", "icao_location"),
            ("Q-code", "qcode"),
            ("Effective", None),
            ("Limits", None),
            ("Radius", "radius_nm"),
        ]
        parts = [f"<b>{html.escape(str(title))}</b>"]
        for label, field_name in rows:
            if label == "Effective":
                start = self._feature_value(feature, "effective_start") or "unknown"
                end = self._feature_value(feature, "effective_end") or "open"
                value = f"{start} to {end}"
            elif label == "Limits":
                lower = self._feature_value(feature, "lower_limit_raw") or "unknown"
                upper = self._feature_value(feature, "upper_limit_raw") or "unknown"
                value = f"{lower} / {upper}"
            else:
                value = self._feature_value(feature, field_name)
                if label == "Radius" and value not in (None, ""):
                    value = f"{value} NM"

            if value not in (None, ""):
                parts.append(f"{html.escape(label)}: {html.escape(str(value))}")

        description = self._feature_value(feature, "description")
        if not description:
            description = self._feature_value(feature, "remarks")
        if description:
            summary = " ".join(str(description).split())
            if len(summary) > 260:
                summary = summary[:257] + "..."
            parts.append("")
            parts.append(html.escape(summary))

        QToolTip.showText(
            QCursor.pos(),
            "<br/>".join(parts),
            self.iface.mapCanvas(),
            self.iface.mapCanvas().rect(),
            15000,
        )

    @staticmethod
    def _filter_options(features) -> dict:
        return {
            "activity_groups": sorted({feature.activity_group for feature in features if feature.activity_group}),
            "firs": sorted({feature.fir for feature in features if feature.fir}),
            "scopes": sorted({feature.scope for feature in features if feature.scope}),
            "qcodes": sorted({feature.qcode[:3] for feature in features if feature.qcode}),
        }

    @staticmethod
    def _static_filter_options(features) -> dict:
        return {
            "static_categories": sorted({feature.category for feature in features if feature.category}),
            "static_types": sorted({feature.airspace_type for feature in features if feature.airspace_type}),
        }

    def _configured_url(self) -> str:
        settings = QSettings()
        return settings.value("uk_airspace_tools/nats_pib_url", DEFAULT_NATS_PIB_URL, type=str)

    def _info(self, message: str) -> None:
        self._log(message, Qgis.Info)
        self.iface.messageBar().pushInfo("UK Airspace Tools", message)

    def _warn(self, message: str) -> None:
        self._log(message, Qgis.Warning)
        self.iface.messageBar().pushWarning("UK Airspace Tools", message)

    @staticmethod
    def _log(message: str, level) -> None:
        try:
            QgsMessageLog.logMessage(message, "UK Airspace Tools", level)
        except Exception:
            pass
