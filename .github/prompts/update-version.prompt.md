---
description: Update the project version in pyproject, manifest, and uv.lock
---

# Update Version

Update the project version number to `$VERSION`.

If `$VERSION` starts with `v`, use the version without the leading `v` in project files.

1. Update `pyproject.toml`:

    ```toml
    version = "$VERSION"
    ```

2. Update `custom_components/haeo/manifest.json`:

    ```json
    {
      "version": "$VERSION"
    }
    ```

3. Run `uv lock` to regenerate the lockfile with the new version.
