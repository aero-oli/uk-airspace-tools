# Changelog

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
