from __future__ import annotations

import sys
import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "uk_airspace_tools"


def _add_qgis_dll_directories() -> None:
    qgis_root = os.environ.get("OSGEO4W_ROOT")
    if not qgis_root:
        return
    root = Path(qgis_root)
    for path in [
        root / "bin",
        root / "apps" / "Qt5" / "bin",
        root / "apps" / "qgis-ltr" / "bin",
        root / "apps" / "Python312",
        root / "apps" / "Python312" / "DLLs",
    ]:
        if path.exists():
            os.add_dll_directory(str(path))


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _qgis_app():
    from qgis.core import QgsApplication

    app = QgsApplication.instance()
    if app is None:
        profile_dir = Path(tempfile.gettempdir()) / "uk_airspace_tools_qgis_smoke"
        auth_dir = profile_dir / "auth"
        auth_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("QGIS_CUSTOM_CONFIG_PATH", str(profile_dir))
        os.environ.setdefault("QGIS_AUTH_DB_DIR_PATH", str(auth_dir))
        app = QgsApplication([], True)
        app.initQgis()
    return app


def _smoke_imports() -> None:
    from uk_airspace_tools import classFactory
    from uk_airspace_tools.providers.nats_aip_dataset import NatsAipDatasetProvider
    from uk_airspace_tools.providers.nats_pib_xml import NatsPibXmlProvider
    from uk_airspace_tools.qgis_layers.layer_manager import LayerManager
    from uk_airspace_tools.tasks import AirspaceRefreshTask
    from uk_airspace_tools.ui.dock_widget import UkAirspaceDockWidget

    _assert(callable(classFactory), "Plugin classFactory is not callable.")
    _assert(NatsPibXmlProvider.display_name, "NOTAM provider display name is missing.")
    _assert(NatsAipDatasetProvider.display_name, "AIP provider display name is missing.")
    _assert(LayerManager.GROUP_NAME == "UK Airspace", "Unexpected NOTAM layer group name.")
    _assert(AirspaceRefreshTask is not None, "Refresh task class did not import.")
    _assert(UkAirspaceDockWidget is not None, "Dock widget class did not import.")


def _smoke_metadata() -> None:
    metadata = (PLUGIN_DIR / "metadata.txt").read_text(encoding="utf-8")
    _assert("icon=icon.svg" in metadata, "metadata.txt does not reference icon.svg.")
    _assert("not a replacement for official briefing" in metadata.lower(), "Operational warning is missing from metadata.")
    _assert((PLUGIN_DIR / "icon.svg").is_file(), "icon.svg is missing.")


def _smoke_dock_widget() -> None:
    from uk_airspace_tools.ui.dock_widget import UkAirspaceDockWidget

    dock = UkAirspaceDockWidget()
    try:
        _assert(dock.selected_source() in {"nats", "local"}, "Dock source selector has an unexpected value.")
        dock.set_refresh_state(True, "Smoke refresh")
        _assert(not dock.refresh_button.isEnabled(), "Refresh button should be disabled while a refresh is running.")
        _assert(dock.cancel_refresh_button.isEnabled(), "Cancel button should be enabled while a refresh is running.")
        dock.set_refresh_state(False, "Idle")
        _assert(dock.refresh_button.isEnabled(), "Refresh button should be enabled after refresh ends.")
        _assert(not dock.cancel_refresh_button.isEnabled(), "Cancel button should be disabled after refresh ends.")
        dock.set_warning_action_state(2)
        _assert(dock.review_warnings_button.isEnabled(), "Warning review button should enable when warnings exist.")
        dock.set_layer_action_state(has_notams=True, has_static_airspace=True, isolation_active=True)
        _assert(dock.zoom_button.isEnabled(), "Zoom button should enable when NOTAM layers exist.")
        _assert(dock.inspect_airspace_button.isEnabled(), "Airspace inspect button should enable when inspectable airspace exists.")
        _assert(dock.clear_isolation_button.isEnabled(), "Clear isolation button should enable when isolation is active.")
    finally:
        dock.close()


def main() -> int:
    skip_widgets = "--skip-widgets" in sys.argv
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    print("Preparing QGIS DLL search paths...", flush=True)
    _add_qgis_dll_directories()
    print("Starting QGIS application...", flush=True)
    _qgis_app()
    print("Checking plugin imports...", flush=True)
    _smoke_imports()
    print("Checking plugin metadata...", flush=True)
    _smoke_metadata()
    if skip_widgets:
        print("Skipping dock widget state checks.", flush=True)
    else:
        print("Checking dock widget state...", flush=True)
        _smoke_dock_widget()
    print("QGIS smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
