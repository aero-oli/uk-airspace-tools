## Summary


## Testing

- [ ] `python -m ruff check .`
- [ ] `.\scripts\build-plugin-zip.ps1`
- [ ] `python -m unittest discover uk_airspace_tools/tests`
- [ ] `python -m compileall -q uk_airspace_tools`
- [ ] `scripts/qgis-smoke-test.py` and `docs/QGIS_TESTING.md` checklist, if UI/layer behaviour changed

## Safety Notes

- [ ] This change does not weaken the operational-use disclaimer.
- [ ] Generated QGIS projects, GeoPackages, release zips, and caches are not committed.
