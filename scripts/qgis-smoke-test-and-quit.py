from __future__ import annotations

import runpy
import sys
import tempfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("qgis-smoke-test.py")
LOG_PATH = Path(tempfile.gettempdir()) / "uk_airspace_tools_qgis_desktop_smoke.log"


def _log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def main() -> int:
    _log("starting desktop smoke runner")
    sys.argv = [str(SCRIPT_PATH)]
    try:
        runpy.run_path(str(SCRIPT_PATH), run_name="__main__")
    except SystemExit as exc:
        code = int(exc.code or 0)
    else:
        code = 0

    _log(f"smoke script finished with code {code}")
    from qgis.PyQt.QtCore import QTimer
    from qgis.PyQt.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        QTimer.singleShot(1000, app.quit)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
