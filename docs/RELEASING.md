# Releasing

Releases are created from version tags. The tag must match the plugin version in `uk_airspace_tools/metadata.txt`.

## Release checklist

1. Update `uk_airspace_tools/metadata.txt` with the new version.
2. Update `CHANGELOG.md` with a matching `## X.Y.Z` section.
3. Run the local checks:

   ```powershell
   python -m unittest discover uk_airspace_tools/tests
   python -m compileall -q uk_airspace_tools
   .\scripts\build-plugin-zip.ps1
   ```

4. Commit the release changes and push `main`.
5. Create and push a matching tag:

   ```powershell
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

The GitHub Actions release workflow verifies the tag matches the plugin metadata version, runs the tests, builds the installable plugin zip, extracts the matching changelog section, and publishes the GitHub Release with the zip attached.

## Versioning

Use semantic versions:

- Patch version for bug fixes and parser/styling improvements.
- Minor version for new data sources, filters, or user-facing tools.
- Major version for breaking changes to stored data, settings, or supported QGIS versions.
