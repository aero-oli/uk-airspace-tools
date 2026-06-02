# Contributing

Thanks for considering a contribution to UK Airspace Tools.

## Development Setup

This is a QGIS Python plugin. Pure parser tests run with normal Python, but QGIS UI and layer-loading behaviour must be tested inside QGIS.

Run the pure-Python test suite from the repository root:

```bash
python -m unittest discover uk_airspace_tools/tests
```

For local QGIS development, link the `uk_airspace_tools` folder into your active QGIS profile's `python/plugins` directory and use the QGIS Plugin Reloader plugin after edits.

## Pull Request Checklist

- Keep source data assumptions explicit.
- Add or update tests for parsers, filters, or schema changes.
- Do not commit generated GeoPackage caches, QGIS projects, release zips, or `__pycache__` folders.
- Manually test QGIS UI changes where practical.
- Preserve the operational warning: this plugin is not a substitute for official briefing or regulatory checks.

## Coding Style

- Prefer standard library code where practical.
- Keep QGIS/PyQt imports guarded so pure-Python tests still run outside QGIS.
- Keep data providers separate from QGIS layer/presentation code.
- Use clear names for aviation fields and preserve raw source values when parsing is ambiguous.
