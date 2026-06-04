## Scope

These instructions apply to the whole repository. This is a QGIS Python plugin named `UK Airspace Tools`; the installable plugin package is `uk_airspace_tools/`.

Do not add nested `AGENTS.md` files unless a subdirectory gains materially different commands or safety rules.

## Change appetite

Do not preserve existing structure for its own sake. If a larger rewrite, rename, deletion of obsolete code, or project restructure produces a cleaner and more maintainable result, it is acceptable.

Before making drastic changes, state the intended change and why, preserve valuable logic/data/user configuration, and avoid destructive removal of important information unless it is clearly obsolete or replaced.

## Setup and core commands

- There is no repo-level dependency manifest at present. Pure parser and utility tests are intended to run with normal Python; QGIS UI, PyQGIS layer loading, and GDAL-backed GeoPackage writing require a QGIS Python environment.
- Run the pure-Python test suite from the repository root:

  ```bash
  python -m unittest discover uk_airspace_tools/tests
  ```

- Run a targeted unittest module when working in one parser/provider area, for example:

  ```bash
  python -m unittest uk_airspace_tools.tests.test_notam_parser
  ```

- Compile-check the plugin package:

  ```bash
  python -m compileall -q uk_airspace_tools
  ```

- Build the QGIS plugin zip from the repository root:

  ```powershell
  .\scripts\build-plugin-zip.ps1
  ```

  The zip is written to `dist/uk_airspace_tools.zip`.

## Validation before finishing

- For parser, provider, geometry, filter, or schema changes, run `python -m unittest discover uk_airspace_tools/tests`.
- For broad Python changes or release preparation, also run `python -m compileall -q uk_airspace_tools`.
- For UI, map canvas, PyQGIS layer-loading, styling, identify-tool, or GeoPackage-writing changes, note that full validation requires manual testing inside QGIS.
- For release changes, follow `docs/RELEASING.md`: metadata version, matching changelog section, tests, compile check, and plugin zip build.

## Repository map

- `uk_airspace_tools/plugin.py` - QGIS plugin entrypoint and application wiring.
- `uk_airspace_tools/parsers/` - NOTAM, Q-line, schedule, and vertical-limit parsing.
- `uk_airspace_tools/providers/` - NATS PIB XML, NATS AIP dataset, and local-file providers.
- `uk_airspace_tools/geometry/` - coordinate parsing and Q-line geometry helpers.
- `uk_airspace_tools/storage/` - GeoPackage schemas and writers.
- `uk_airspace_tools/qgis_layers/` - QGIS layer management, styles, and identify tools.
- `uk_airspace_tools/ui/` - dock widget and cross-section dialog.
- `uk_airspace_tools/tests/` - pure-Python unittest coverage.
- `scripts/build-plugin-zip.ps1` - release zip builder.
- `.github/workflows/` - unit-test and release automation.

## Conventions

- Prefer standard-library code where practical.
- Keep QGIS/PyQt imports guarded or localized so pure-Python tests can still run outside QGIS.
- Keep data providers separate from QGIS layer and presentation code.
- Preserve raw source values when parsing is ambiguous, and keep source-data assumptions explicit.
- Use clear aviation field names.
- Preserve the operational warning: this plugin is for visualisation and situational awareness only, not official pre-flight briefing, regulatory review, or operational flight planning.

## Boundaries and safety

- Do not commit generated GeoPackage caches, QGIS project files, release zips, build output, Python caches, or local environment files. See `.gitignore`.
- Do not commit API keys, credentials, private operational data, or personal flight-planning data. The plugin downloads public NATS/AIS datasets and does not require secrets.
- NATS/AIS dataset URLs and structures can change; retain local-file import paths as fallbacks unless intentionally replacing them.
- When touching release logic, remember that GitHub release tags must match `version=` in `uk_airspace_tools/metadata.txt`.

## References

- `README.md` - installation, development, data sources, safety notes, and repository layout.
- `CONTRIBUTING.md` - test command, PR checklist, and coding style.
- `docs/RELEASING.md` - release checklist and versioning.
- `.github/PULL_REQUEST_TEMPLATE.md` - expected testing and safety notes.
- `SECURITY.md` - data, network, and operational safety guidance.
