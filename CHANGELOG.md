# Changelog

## 0.2.0 - 2026-06-04

- Move NOTAM and permanent-airspace refresh work into background QGIS tasks with refresh state, cancellation, and clearer failure reporting.
- Add a parse-warning review action and richer refresh/source/status diagnostics in the dock.
- Add separate NOTAM and permanent-airspace map-tip templates.
- Store permanent-airspace records without geometry in a non-spatial table instead of polygon layers.
- Improve AIXM geometry conversion for `posList`, interior rings, multiple surfaces, multipolygons, and radius unit conversion.
- Add a plugin icon, metadata tags, Ruff linting, architecture notes, and a QGIS manual validation checklist.
- Add a QGIS smoke-test script for plugin imports, metadata/icon checks, and dock state checks.
- Add provider discovery/error tests, static-cache routing tests, task-helper tests, and layer-filter diagnostics tests.

## 0.1.0

Initial public release candidate.

- Fetch and parse NATS PIB XML NOTAMs.
- Parse structured NATS PIB XML into NOTAM features.
- Parse Q-line centre/radius geometry, vertical limits, and validity dates.
- Fetch and parse the NATS UK ICAO AIP Dataset for permanent airspace.
- Load local NOTAM XML and local AIP XML/KML/KMZ/ZIP files.
- Cache NOTAM and permanent airspace data into GeoPackage layers.
- Add QGIS layer groups for NOTAMs and permanent airspace.
- Filter NOTAMs by date/time, status, activity, FIR, scope, Q-code, radius, altitude, and keyword.
- Filter permanent airspace by category, type, altitude, and keyword.
- Inspect NOTAMs from map clicks.
- Inspect permanent airspace from map clicks with a vertical cross-section diagram.
- Isolate selected cross-section airspace features on the map.
