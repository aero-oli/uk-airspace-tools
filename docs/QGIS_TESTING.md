# QGIS Manual Testing Checklist

Run this checklist in QGIS before release or after changes to refresh tasks, layer loading, styling, identify tools, map tips, or GeoPackage writing.

## Setup

1. Install or link `uk_airspace_tools/` into the active QGIS profile plugin directory.
2. Restart QGIS or reload the plugin.
3. Open a new empty QGIS project.
4. Open `Plugins -> UK Airspace Tools -> Open UK Airspace Panel`.

## Smoke Test Script

Before the manual click-through, run `scripts/qgis-smoke-test.py` inside a configured QGIS Python environment.

For a full shell-based smoke test:

```powershell
scripts\run-qgis-smoke-test.bat
```

On headless shells where Qt widgets cannot be created or QGIS desktop cannot execute startup code unattended, run the import/metadata-only path:

```powershell
scripts\run-qgis-smoke-test.bat --skip-widgets
```

If shell environment setup is unreliable, open the QGIS Python console and run the full widget check:

```python
exec(open(r"C:\path\to\UK Airspace Tools\scripts\qgis-smoke-test.py", encoding="utf-8").read())
```

The full script verifies PyQGIS imports, plugin imports, metadata/icon presence, dock widget refresh state, warning-review controls, and layer action state. The `--skip-widgets` mode verifies PyQGIS imports, plugin imports, and metadata/icon presence only.

## NOTAM Refresh

1. Click `Refresh NOTAMs`.
2. Confirm the panel remains responsive while the refresh task runs.
3. Confirm `Cancel Refresh` is enabled while the task is running and disabled when it completes.
4. Confirm the status area shows the latest source, refresh status, last refresh time, feature counts, and warning count.
5. Confirm the `UK Airspace` group appears with:
   - `NOTAM polygons`
   - `NOTAM points`
   - `NOTAM text-only`
6. Toggle polygon, point, and text-only checkboxes and confirm layer visibility updates.
7. Use date, status, radius, altitude, Q-code, FIR, and keyword filters and confirm subset updates do not produce message-log errors.
8. Hover/click NOTAM features and confirm map tips/details use NOTAM fields.
9. Click `Inspect NOTAM`, then click inside and outside visible NOTAM geometry.
10. If warnings are present, click `Review Parse Warnings` and confirm feature IDs and warning text are readable.

## Local NOTAM File

1. Click `Load NOTAM XML File`.
2. Select a known local XML fixture or saved PIB file.
3. Confirm source status shows the local file path.
4. Confirm layers and filters behave as for live refresh.

## Permanent Airspace Refresh

1. Click `Refresh Permanent Airspace`.
2. Confirm the panel remains responsive while the task runs.
3. Confirm the `UK Permanent Airspace` group appears with category layers and `Permanent airspace records without geometry`.
4. Confirm polygon layers display with permanent-airspace styling.
5. Confirm the non-spatial records layer/table is loaded but not used by cross-section inspection.
6. Use category, type, altitude, and keyword filters.
7. Hover/click permanent-airspace features and confirm map tips/details use permanent-airspace fields.
8. Click `Inspect / Cross-section`, click a point inside overlapping permanent airspace, and confirm the dialog shows vertically sorted bands.
9. Click a band and confirm map isolation shows only that feature.
10. Click `Show Filtered Airspace` and confirm normal filters are restored.

## Local AIP Dataset

1. Click `Load AIP XML/KML File`.
2. Select a known AIXM XML, KML, KMZ, or ZIP dataset.
3. Confirm source status shows the local file path or archive member.
4. Confirm polygon, multipolygon, and geometry-less records load into the expected layers.

## Task Cancellation And Failure Paths

1. Start a live refresh and click `Cancel Refresh` while it is running.
2. Confirm the status changes to cancelled and no partial layers replace existing good layers.
3. Configure an invalid NOTAM URL via QGIS settings or test build, then refresh.
4. Confirm the error message identifies the failed source and phase.
5. Load an invalid local file and confirm the previous loaded layers remain available.

## Release Smoke Test

1. Run `.\scripts\build-plugin-zip.ps1`.
2. Install `dist/uk_airspace_tools.zip` through QGIS plugin manager.
3. Confirm the plugin icon appears in plugin metadata/menu/toolbar.
4. Repeat one live NOTAM refresh and one permanent-airspace refresh.

Record the QGIS version, operating system, test date, and any warnings or manual deviations in the release notes or PR checklist.
