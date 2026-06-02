# Security Policy

## Reporting Issues

Please do not report security issues in public issues if they involve sensitive data, credentials, or a live exploit path.

Report security concerns privately to the repository owner.

## Data And Network Notes

UK Airspace Tools downloads public NATS/AIS datasets at runtime. It does not require credentials and should not store secrets.

Do not put API keys, credentials, private operational data, or personal flight planning data into committed files. The repository `.gitignore` excludes common local environment files and generated QGIS/GeoPackage artifacts.

## Operational Safety

This plugin is for visualisation only. It must not be relied on as the sole source for aviation decisions, regulatory compliance, or pre-flight briefing.
