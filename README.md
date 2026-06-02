# UK Airspace Tools

UK Airspace Tools is a QGIS Python plugin for viewing UK NOTAMs and permanent UK airspace datasets in a QGIS project.

It can fetch and parse current UK NOTAM PIB XML, fetch the current NATS UK ICAO AIP Dataset, cache the data into GeoPackage layers, style those layers, filter them by date/altitude/type, and inspect airspace with a vertical cross-section diagram.

This plugin is an aid for visualisation and situational awareness only. It is not a replacement for official pre-flight briefing, NOTAM checking, regulatory review, or operational flight planning.

## Features

- Fetch UK NOTAM PIB XML and parse structured NATS PIB NOTAM records.
- Fetch the current NATS UK ICAO AIP Dataset for permanent airspace.
- Load local NOTAM XML and local AIP XML/KML/KMZ/ZIP files.
- Create QGIS layer groups for NOTAMs and permanent airspace.
- Filter NOTAMs by date/time, status, activity, FIR, scope, Q-code, radius, altitude, and keyword.
- Filter permanent airspace by category, type, altitude, and keyword.
- Inspect NOTAMs at a clicked map point.
- Inspect permanent airspace at a clicked map point and show a vertical cross-section diagram.
- Click a cross-section block to isolate that airspace feature on the map.

## Data Sources

The plugin fetches public NATS/AIS datasets at runtime:

- NOTAM PIB XML: `https://pibs.nats.co.uk/operational/pibs/PIB.xml`
- NATS digital datasets page: `https://nats-uk.ead-it.com/cms-nats/opencms/en/Publications/digital-datasets/`

Dataset structures and URLs can change. Local file import is retained as a fallback.

## Install In QGIS

Copy the `uk_airspace_tools` folder into your QGIS profile plugin directory.

Typical plugin directories:

- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins`
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`

Then restart QGIS and enable `UK Airspace Tools` in `Plugins -> Manage and Install Plugins`.

For development on Windows, use a junction so QGIS loads the source folder directly:

```powershell
$source = "C:\path\to\UK Airspace Tools\uk_airspace_tools"
$plugins = "$env:APPDATA\QGIS\QGIS3\profiles\default\python\plugins"
$link = Join-Path $plugins "uk_airspace_tools"

New-Item -ItemType Directory -Force -Path $plugins | Out-Null
New-Item -ItemType Junction -Path $link -Target $source
```

If your active profile is not `default`, use `Settings -> User Profiles -> Open Active Profile Folder` in QGIS and place/link the plugin under that profile's `python/plugins` directory.

## Build A Release Zip

From the repository root:

```powershell
.\scripts\build-plugin-zip.ps1
```

The output is written to `dist/uk_airspace_tools.zip`. That zip contains the `uk_airspace_tools` plugin folder at the archive root, which is the layout QGIS expects.

## Development

Parser and utility tests run outside QGIS:

```bash
python -m unittest discover uk_airspace_tools/tests
```

The QGIS UI, map canvas integration, PyQGIS layer loading, and GDAL-backed GeoPackage writing require a QGIS Python environment for full manual testing.

## Repository Layout

```text
uk_airspace_tools/
├── geometry/        # Coordinate and Q-line geometry helpers
├── parsers/         # NOTAM and vertical-limit parsers
├── providers/       # NATS PIB, NATS AIP, and local file providers
├── qgis_layers/     # QGIS layer loading, styling, identify tools
├── storage/         # GeoPackage schemas/writers
├── tests/           # Pure-Python unit tests
├── ui/              # QGIS dock widgets and cross-section dialog
├── metadata.txt     # QGIS plugin metadata
└── __init__.py      # QGIS plugin entrypoint
```

## Safety And Limitations

- Do not use this plugin as the sole source for flight planning or regulatory compliance.
- NOTAM geometry is conservative and depends on available Q-line geometry.
- Permanent airspace geometry is parsed from the NATS AIXM/KML datasets and should be checked against official sources for operational use.
- Some complex airspace boundaries and annotations can be simplified for display.
- Internet access is required for live NATS refreshes.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
