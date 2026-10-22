---
name: update-version
description: Bump the HAEO version consistently across pyproject.toml, custom_components/haeo/manifest.json, and uv.lock. Use when asked to set, bump, or release a version, when the version consistency gate fails, or when a release tag does not match the project version.
---

# Update version

Update the project version number to `$VERSION`.

If `$VERSION` starts with `v`, use the version without the leading `v` in project files.
The version is PEP 440 style, `X.Y.Z` with an optional `rcN`, `aN`, or `bN` suffix, such as `0.5.0rc1`.
The release workflow rejects a tag in any other form, or one that does not match both files.

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

4. Run `uv run check version` to confirm the two files agree.
