# Architecture

UK Airspace Tools is split into small layers so parser/provider work can be tested without QGIS.

## Runtime Flow

1. UI actions in `ui/dock_widget.py` emit requests.
2. `plugin.py` creates an `AirspaceRefreshTask`.
3. `tasks.py` fetches source data, parses records, and writes a GeoPackage cache off the QGIS UI thread.
4. The task completion callback in `plugin.py` loads the generated GeoPackage into the QGIS project.
5. `qgis_layers/layer_manager.py` applies layer styling, map tips, visibility, and subset filters.

QGIS project mutations should stay out of task `run()` methods. Provider fetches, parser work, and cache writes are safe to keep in background tasks.

## Data Boundaries

- `providers/` fetch public NATS/AIS data or local files and return parsed feature records.
- `parsers/` preserve raw values when data is ambiguous and attach parse warnings instead of hiding assumptions.
- `storage/` writes GeoPackage layers and metadata. Spatial permanent-airspace records go to category polygon layers; records without geometry go to `permanent_airspace_text_only`.
- `qgis_layers/` owns QGIS layer loading, styling, filtering, and map-tip templates.
- `ui/` owns controls and display state, but not data fetching or parsing.

## Validation

Pure parser, provider, filter, and routing changes should pass:

```bash
python -m ruff check .
python -m unittest discover uk_airspace_tools/tests
python -m compileall -q uk_airspace_tools
```

Refresh tasks, layer loading, styling, identify tools, and GeoPackage writing still require manual validation inside QGIS.
