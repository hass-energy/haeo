#!/usr/bin/env python3
"""CLI tool to snapshot and restore Home Assistant config/.storage state.

Local developer tool for testing migrations between HAEO/HA versions:

    uv run snapshot save [--label NAME]
    uv run snapshot list
    uv run snapshot restore <id|prefix|label|latest> [--no-backup]
    uv run snapshot delete <id|prefix> [--force]

Each snapshot lives at ``config/.snapshots/<haeo-version>__<UTC-timestamp>[__label]/``
and contains the integration's ``.storage/`` tree plus ``HA_VERSION``, plus a
``meta.json`` describing it.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Final

REPO_ROOT: Final = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR: Final = REPO_ROOT / "config"
MANIFEST_PATH: Final = REPO_ROOT / "custom_components" / "haeo" / "manifest.json"

SNAPSHOTS_DIRNAME: Final = ".snapshots"
STORAGE_DIRNAME: Final = ".storage"
HA_VERSION_FILENAME: Final = ".HA_VERSION"
PID_FILENAME: Final = "home-assistant.pid"
META_FILENAME: Final = "meta.json"
SNAPSHOT_STORAGE_DIRNAME: Final = "storage"
SNAPSHOT_HA_VERSION_FILENAME: Final = "HA_VERSION"

_SIZE_UNIT_STEP: Final = 1024
_SIZE_UNITS: Final = ("B", "KB", "MB", "GB", "TB")


class SnapshotError(Exception):
    """Raised for user-facing snapshot tool failures."""


@dataclass(frozen=True)
class SnapshotInfo:
    """In-memory representation of a snapshot on disk."""

    snapshot_dir: Path
    meta: dict[str, Any]


def read_haeo_version() -> str:
    """Read the current HAEO version from custom_components/haeo/manifest.json."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    return str(manifest["version"])


def _format_id_timestamp(dt: datetime) -> str:
    """Compact UTC timestamp for snapshot ids: YYYYMMDDTHHMMSSZ."""
    return dt.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _now() -> datetime:
    return datetime.now(UTC)


def _snapshots_root(config_dir: Path) -> Path:
    return config_dir / SNAPSHOTS_DIRNAME


def _ensure_ha_stopped(config_dir: Path, *, force: bool) -> None:
    if force:
        return
    pid_file = config_dir / PID_FILENAME
    if pid_file.exists():
        msg = f"Home Assistant appears to be running ({pid_file} exists). Stop HA first, or pass --force to override."
        raise SnapshotError(msg)


def _atomic_replace(src: Path, dst: Path) -> None:
    """Rename ``src`` to ``dst`` atomically.

    Wrapped in a module-level function so tests can monkey-patch it to
    simulate a mid-restore failure.
    """
    src.replace(dst)


def _read_meta(snapshot_dir: Path) -> dict[str, Any]:
    return json.loads((snapshot_dir / META_FILENAME).read_text())


def create_snapshot(
    *,
    config_dir: Path,
    haeo_version: str,
    label: str | None = None,
    now: datetime | None = None,
    force: bool = False,
) -> SnapshotInfo:
    """Snapshot ``config/.storage/`` and ``.HA_VERSION`` to a new directory."""
    storage_src = config_dir / STORAGE_DIRNAME
    if not storage_src.is_dir():
        msg = f"No .storage directory found at {storage_src}"
        raise SnapshotError(msg)

    _ensure_ha_stopped(config_dir, force=force)

    timestamp = now or _now()
    snapshot_id = f"{haeo_version}__{_format_id_timestamp(timestamp)}"
    if label:
        snapshot_id = f"{snapshot_id}__{label}"

    snapshot_dir = _snapshots_root(config_dir) / snapshot_id
    if snapshot_dir.exists():
        msg = f"Snapshot {snapshot_id} already exists at {snapshot_dir}"
        raise SnapshotError(msg)

    snapshot_dir.mkdir(parents=True)

    try:
        shutil.copytree(storage_src, snapshot_dir / SNAPSHOT_STORAGE_DIRNAME)

        ha_version_src = config_dir / HA_VERSION_FILENAME
        ha_version_value = ha_version_src.read_text() if ha_version_src.exists() else ""
        (snapshot_dir / SNAPSHOT_HA_VERSION_FILENAME).write_text(ha_version_value)

        meta = {
            "haeo_version": haeo_version,
            "ha_version": ha_version_value,
            "created_at": timestamp.astimezone(UTC).isoformat(),
            "label": label,
        }
        (snapshot_dir / META_FILENAME).write_text(json.dumps(meta, indent=2) + "\n")
    except Exception:
        shutil.rmtree(snapshot_dir, ignore_errors=True)
        raise

    return SnapshotInfo(snapshot_dir=snapshot_dir, meta=meta)


def list_snapshots(*, config_dir: Path) -> list[SnapshotInfo]:
    """Return all snapshots, newest-first by ``created_at``."""
    root = _snapshots_root(config_dir)
    if not root.is_dir():
        return []

    snapshots: list[SnapshotInfo] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / META_FILENAME
        if not meta_path.is_file():
            continue
        snapshots.append(SnapshotInfo(snapshot_dir=entry, meta=_read_meta(entry)))

    snapshots.sort(key=lambda s: str(s.meta.get("created_at", "")), reverse=True)
    return snapshots


def find_snapshots(*, config_dir: Path, query: str) -> list[Path]:
    """Resolve a query to one or more snapshot directories.

    Order of precedence:

    1. ``latest`` keyword -> [newest snapshot]
    2. Exact id match (snapshot dir name)
    3. Exact label match
    4. Id prefix match (may return many)
    """
    snapshots = list_snapshots(config_dir=config_dir)
    if not snapshots:
        return []

    if query == "latest":
        return [snapshots[0].snapshot_dir]

    exact = [s for s in snapshots if s.snapshot_dir.name == query]
    if exact:
        return [s.snapshot_dir for s in exact]

    by_label = [s for s in snapshots if s.meta.get("label") == query]
    if by_label:
        return [s.snapshot_dir for s in by_label]

    prefix = [s for s in snapshots if s.snapshot_dir.name.startswith(query)]
    return [s.snapshot_dir for s in prefix]


def resolve_snapshot(*, config_dir: Path, query: str) -> Path:
    """Resolve a query to exactly one snapshot directory or raise."""
    matches = find_snapshots(config_dir=config_dir, query=query)
    if not matches:
        msg = f"no snapshot matches {query!r}"
        raise SnapshotError(msg)
    if len(matches) > 1:
        names = ", ".join(p.name for p in matches)
        msg = f"{query!r} matches multiple snapshots: {names}"
        raise SnapshotError(msg)
    return matches[0]


def restore_snapshot(
    *,
    config_dir: Path,
    query: str,
    haeo_version: str,
    backup: bool = True,
    force: bool = False,
    now: datetime | None = None,
) -> SnapshotInfo:
    """Restore ``config/.storage`` and ``.HA_VERSION`` from a snapshot."""
    _ensure_ha_stopped(config_dir, force=force)

    source_dir = resolve_snapshot(config_dir=config_dir, query=query)
    source_meta = _read_meta(source_dir)

    if backup:
        create_snapshot(
            config_dir=config_dir,
            haeo_version=haeo_version,
            label="pre-restore",
            now=now,
            force=force,
        )

    storage_dst = config_dir / STORAGE_DIRNAME
    storage_staging = config_dir / f"{STORAGE_DIRNAME}.new"
    storage_old = config_dir / f"{STORAGE_DIRNAME}.old"
    ha_version_dst = config_dir / HA_VERSION_FILENAME
    ha_version_old = config_dir / f"{HA_VERSION_FILENAME}.old"

    for stale in (storage_staging, storage_old, ha_version_old):
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()

    shutil.copytree(source_dir / SNAPSHOT_STORAGE_DIRNAME, storage_staging)

    moved_storage = False
    moved_ha_version = False

    try:
        if storage_dst.exists():
            _atomic_replace(storage_dst, storage_old)
            moved_storage = True
        _atomic_replace(storage_staging, storage_dst)

        snapshot_ha_version = source_dir / SNAPSHOT_HA_VERSION_FILENAME
        if snapshot_ha_version.exists():
            if ha_version_dst.exists():
                _atomic_replace(ha_version_dst, ha_version_old)
                moved_ha_version = True
            shutil.copyfile(snapshot_ha_version, ha_version_dst)
    except Exception:
        shutil.rmtree(storage_staging, ignore_errors=True)
        if moved_storage and storage_old.exists():
            if storage_dst.exists():
                shutil.rmtree(storage_dst)
            storage_old.rename(storage_dst)
        if moved_ha_version and ha_version_old.exists():
            if ha_version_dst.exists():
                ha_version_dst.unlink()
            ha_version_old.rename(ha_version_dst)
        raise

    if storage_old.is_dir():
        shutil.rmtree(storage_old)
    if ha_version_old.exists():
        ha_version_old.unlink()

    return SnapshotInfo(snapshot_dir=source_dir, meta=source_meta)


def delete_snapshot(
    *,
    config_dir: Path,
    query: str,
    force: bool = False,
) -> list[str]:
    """Delete one or more snapshots. Returns the list of removed ids."""
    matches = find_snapshots(config_dir=config_dir, query=query)
    if not matches:
        msg = f"no snapshot matches {query!r}"
        raise SnapshotError(msg)
    if len(matches) > 1 and not force:
        names = ", ".join(p.name for p in matches)
        msg = f"{query!r} matches multiple snapshots: {names}. Pass --force to delete all."
        raise SnapshotError(msg)

    removed: list[str] = []
    for path in matches:
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


def _human_size(path: Path) -> str:
    total = float(sum(p.stat().st_size for p in path.rglob("*") if p.is_file()))
    for unit in _SIZE_UNITS[:-1]:
        if total < _SIZE_UNIT_STEP:
            return f"{total:.1f}{unit}"
        total /= _SIZE_UNIT_STEP
    return f"{total:.1f}{_SIZE_UNITS[-1]}"


def _print_snapshot_table(snapshots: list[SnapshotInfo]) -> None:
    if not snapshots:
        print("No snapshots found.")
        return
    rows = [
        (
            s.snapshot_dir.name,
            str(s.meta.get("haeo_version", "")),
            str(s.meta.get("ha_version", "")).strip(),
            str(s.meta.get("created_at", "")),
            str(s.meta.get("label") or ""),
            _human_size(s.snapshot_dir),
        )
        for s in snapshots
    ]
    headers = ("ID", "HAEO", "HA", "Created", "Label", "Size")
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*("-" * w for w in widths)))
    for row in rows:
        print(fmt.format(*row))


def _cmd_save(args: argparse.Namespace) -> int:
    info = create_snapshot(
        config_dir=args.config_dir,
        haeo_version=args.haeo_version,
        label=args.label,
        force=args.force,
    )
    print(f"Saved snapshot: {info.snapshot_dir.name}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    _print_snapshot_table(list_snapshots(config_dir=args.config_dir))
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    info = restore_snapshot(
        config_dir=args.config_dir,
        query=args.query,
        haeo_version=args.haeo_version,
        backup=not args.no_backup,
        force=args.force,
    )
    print(f"Restored from snapshot: {info.snapshot_dir.name}")
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    removed = delete_snapshot(
        config_dir=args.config_dir,
        query=args.query,
        force=args.force,
    )
    for name in removed:
        print(f"Deleted: {name}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config-dir",
        type=Path,
        default=DEFAULT_CONFIG_DIR,
        help=f"HA config directory (default: {DEFAULT_CONFIG_DIR})",
    )
    common.add_argument(
        "--haeo-version",
        default=None,
        help="HAEO version to tag the snapshot with (default: read from manifest.json)",
    )
    common.add_argument(
        "--force",
        action="store_true",
        help="Bypass safety checks (e.g. running HA, multi-match delete)",
    )

    parser = argparse.ArgumentParser(
        prog="snapshot",
        description="Snapshot and restore Home Assistant config/.storage state.",
        parents=[common],
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    save = subparsers.add_parser("save", parents=[common], help="Save a new snapshot")
    save.add_argument("--label", default=None, help="Optional label suffix for the snapshot id")
    save.set_defaults(func=_cmd_save)

    listing = subparsers.add_parser("list", parents=[common], help="List existing snapshots")
    listing.set_defaults(func=_cmd_list)

    restore = subparsers.add_parser("restore", parents=[common], help="Restore from a snapshot")
    restore.add_argument("query", help="Snapshot id, label, prefix, or 'latest'")
    restore.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the auto pre-restore backup snapshot",
    )
    restore.set_defaults(func=_cmd_restore)

    delete = subparsers.add_parser("delete", parents=[common], help="Delete one or more snapshots")
    delete.add_argument("query", help="Snapshot id, label, or prefix")
    delete.set_defaults(func=_cmd_delete)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the ``snapshot`` console script."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.haeo_version is None:
        args.haeo_version = read_haeo_version()

    try:
        return int(args.func(args))
    except SnapshotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
