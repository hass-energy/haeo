"""Assemble a versioned documentation site.

Combines a freshly built ``main`` site with ``docs.zip`` assets downloaded from
every GitHub Release that has one attached, producing a single tree ready to
upload as a GitHub Pages artifact.

Output layout::

    output/
        main/           # freshly built main docs
        0.4.0rc1/       # unzipped release asset
        0.3.3/          # unzipped release asset
        ...
        dev/            # full copy of main/ (alias)
        latest/         # full copy of newest non-rc release (alias)
        versions.json   # mike-format version manifest read by the theme
        index.html      # root redirect to ./latest/
        CNAME           # custom domain for GitHub Pages

The script shells out to ``gh`` to list releases and download assets; it
therefore requires ``gh`` to be on ``PATH`` and ``GH_TOKEN`` / ``GITHUB_TOKEN``
to be set in the environment.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any
import zipfile

DEFAULT_CNAME = "haeo.io"
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:rc(\d+))?$")


def docs_asset_name(tag: str) -> str:
    """Return the expected docs asset filename for a release tag (e.g. ``docs-v0.3.3.zip``)."""
    return f"docs-{tag}.zip"


@dataclass(frozen=True)
class Release:
    """Parsed release reference."""

    tag: str
    version: str
    sort_key: tuple[int, int, int, int]
    is_rc: bool


def parse_tag(tag: str) -> Release | None:
    """Parse a ``vX.Y.Z[rcN]`` tag into a Release, or return None if unsupported."""
    match = TAG_RE.match(tag)
    if match is None:
        return None
    major = int(match.group(1))
    minor = int(match.group(2))
    patch = int(match.group(3))
    rc_raw = match.group(4)
    is_rc = rc_raw is not None
    # Within the same X.Y.Z, stable releases should sort *newer* than their RCs.
    # `releases.sort(..., reverse=True)` puts larger tuples first, so use a large
    # sentinel for the stable rc_rank to float it above any rcN.
    rc_rank = int(rc_raw) if rc_raw is not None else sys.maxsize
    return Release(tag=tag, version=tag[1:], sort_key=(major, minor, patch, rc_rank), is_rc=is_rc)


def fetch_releases(repo: str) -> list[Release]:
    """Return releases (newest first) that have a ``docs-<tag>.zip`` asset attached."""
    result = subprocess.run(  # noqa: S603 (invoking trusted gh CLI tool)
        ["gh", "api", f"repos/{repo}/releases", "--paginate"],  # noqa: S607 (gh is a trusted first-party CLI tool)
        capture_output=True,
        text=True,
        check=True,
    )
    payload: list[dict[str, Any]] = json.loads(result.stdout)
    releases: list[Release] = []
    for entry in payload:
        tag = str(entry.get("tag_name") or "")
        parsed = parse_tag(tag)
        if parsed is None:
            continue
        assets = entry.get("assets") or []
        names = {str(asset.get("name") or "") for asset in assets}
        expected = docs_asset_name(tag)
        if expected not in names:
            print(f"  skipping {tag}: no {expected} asset")
            continue
        releases.append(parsed)
    releases.sort(key=lambda r: r.sort_key, reverse=True)
    return releases


def _safe_extract(archive: zipfile.ZipFile, dest: Path) -> None:
    """Extract ``archive`` into ``dest`` while rejecting Zip Slip path traversal.

    Even though our zips come from trusted release assets, validating each member
    keeps us safe if an asset is ever replaced or tampered with.
    """
    dest_root = dest.resolve()
    for member in archive.infolist():
        name = member.filename
        if name.startswith("/") or "\\" in name or ".." in Path(name).parts:
            msg = f"refusing to extract unsafe zip entry: {name!r}"
            raise ValueError(msg)
        target = (dest_root / name).resolve()
        try:
            target.relative_to(dest_root)
        except ValueError as exc:
            msg = f"zip entry escapes destination: {name!r}"
            raise ValueError(msg) from exc
    archive.extractall(dest)


def download_docs(repo: str, tag: str, dest: Path) -> None:
    """Download the release's ``docs-<tag>.zip`` asset and extract it into ``dest``."""
    asset = docs_asset_name(tag)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(  # noqa: S603 (invoking trusted gh CLI tool)
            [  # noqa: S607 (gh is a trusted first-party CLI tool)
                "gh",
                "release",
                "download",
                tag,
                "--repo",
                repo,
                "--pattern",
                asset,
                "--dir",
                td,
            ],
            check=True,
        )
        zip_path = Path(td) / asset
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as archive:
            _safe_extract(archive, dest)


def copy_tree(src: Path, dst: Path) -> None:
    """Replace ``dst`` with a recursive copy of ``src``."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def write_redirect(path: Path, target: str) -> None:
    """Write an HTML meta-refresh redirect at ``path`` pointing to ``./{target}/``."""
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>Redirecting to {target}/</title>\n"
        f'  <meta http-equiv="refresh" content="0; url=./{target}/">\n'
        f'  <link rel="canonical" href="./{target}/">\n'
        "</head>\n"
        "<body>\n"
        f'  <p>Redirecting to <a href="./{target}/">{target}/</a>.</p>\n'
        "</body>\n"
        "</html>\n"
    )
    path.write_text(html, encoding="utf-8")


def build_version_entries(
    releases: list[Release],
    latest: Release | None,
    main_version: str,
    dev_alias: str,
    latest_alias: str,
) -> list[dict[str, Any]]:
    """Build the mike-format ``versions.json`` payload (newest first, ``main`` on top)."""
    entries: list[dict[str, Any]] = [
        {"version": main_version, "title": main_version, "aliases": [dev_alias]},
    ]
    for release in releases:
        aliases: list[str] = []
        if latest is not None and release.tag == latest.tag:
            aliases.append(latest_alias)
        entries.append({"version": release.version, "title": release.version, "aliases": aliases})
    return entries


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-site", type=Path, required=True, help="Freshly built main site directory.")
    parser.add_argument("--output", type=Path, required=True, help="Destination tree to write.")
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY"),
        help="owner/repo (defaults to $GITHUB_REPOSITORY).",
    )
    parser.add_argument("--cname", default=DEFAULT_CNAME, help="Custom domain to write as CNAME.")
    parser.add_argument("--main-version", default="main", help="Subdirectory name for the main build.")
    parser.add_argument("--dev-alias", default="dev", help="Alias for the main build.")
    parser.add_argument("--latest-alias", default="latest", help="Alias for the newest non-rc release.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point — see module docstring for behaviour."""
    args = _parse_args(argv)
    repo: str | None = args.repo
    if not repo:
        print("error: --repo or GITHUB_REPOSITORY must be set", file=sys.stderr)
        return 2

    main_site: Path = args.main_site
    output: Path = args.output
    if not main_site.is_dir():
        print(f"error: main site directory not found: {main_site}", file=sys.stderr)
        return 2

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)

    main_version: str = args.main_version
    dev_alias: str = args.dev_alias
    latest_alias: str = args.latest_alias

    main_dir = output / main_version
    print(f"Copying main site -> {main_dir}")
    shutil.copytree(main_site, main_dir)

    print(f"Listing releases for {repo}")
    releases = fetch_releases(repo)
    print(f"Found {len(releases)} release(s) with a docs-<tag>.zip asset")
    for release in releases:
        rel_dir = output / release.version
        print(f"Downloading {release.tag} -> {rel_dir}")
        download_docs(repo, release.tag, rel_dir)

    latest: Release | None = next((r for r in releases if not r.is_rc), None)
    if latest is not None:
        print(f"Aliasing {latest_alias}/ -> {latest.version}/")
        copy_tree(output / latest.version, output / latest_alias)
    else:
        print("No non-rc release available; skipping latest alias")

    print(f"Aliasing {dev_alias}/ -> {main_version}/")
    copy_tree(main_dir, output / dev_alias)

    entries = build_version_entries(releases, latest, main_version, dev_alias, latest_alias)
    versions_path = output / "versions.json"
    versions_path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {versions_path} ({len(entries)} entries)")

    redirect_target = latest_alias if latest is not None else main_version
    write_redirect(output / "index.html", redirect_target)
    print(f"Wrote root redirect -> ./{redirect_target}/")

    cname: str = args.cname
    (output / "CNAME").write_text(cname + "\n", encoding="utf-8")
    print(f"Wrote CNAME={cname}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
