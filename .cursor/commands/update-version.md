# Update Version

Update the project version number to `$VERSION`.

1. Update `pyproject.toml`:
   ```toml
   version = "$VERSION"
   ```

2. Update `custom_components/amber_express/manifest.json`:
   ```json
   "version": "$VERSION"
   ```

3. Run `uv lock` to regenerate the lockfile with the new version.
