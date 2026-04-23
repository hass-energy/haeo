"""Tests for the snapshot CLI tool."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import pytest

from tools import snapshot

FIXED_DT = datetime(2026, 4, 22, 20, 41, 30, tzinfo=UTC)
FIXED_ID = "0.4.0rc1__20260422T204130Z"


@pytest.fixture
def fake_config(tmp_path: Path) -> Path:
    """Create a minimal HA config dir with .storage and .HA_VERSION."""
    config = tmp_path / "config"
    storage = config / ".storage"
    storage.mkdir(parents=True)
    (storage / "core.config_entries").write_text('{"entries": []}')
    (storage / "core.entity_registry").write_text('{"entities": []}')
    (config / ".HA_VERSION").write_text("2026.1.1")
    return config


def test_save_creates_snapshot_dir_with_expected_id(fake_config: Path) -> None:
    """Save creates a directory named <haeo>__<UTC-timestamp>."""
    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        now=FIXED_DT,
    )

    assert info.snapshot_dir == fake_config / ".snapshots" / FIXED_ID
    assert info.snapshot_dir.is_dir()


def test_save_copies_storage_recursively(fake_config: Path) -> None:
    """Storage subdirectories and files are copied verbatim."""
    nested = fake_config / ".storage" / "subdir"
    nested.mkdir()
    (nested / "deep.json").write_text('{"deep": true}')

    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        now=FIXED_DT,
    )

    assert (info.snapshot_dir / "storage" / "core.config_entries").read_text() == '{"entries": []}'
    assert (info.snapshot_dir / "storage" / "subdir" / "deep.json").read_text() == '{"deep": true}'


def test_save_copies_ha_version(fake_config: Path) -> None:
    """The .HA_VERSION file is copied into the snapshot."""
    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        now=FIXED_DT,
    )

    assert (info.snapshot_dir / "HA_VERSION").read_text() == "2026.1.1"


def test_save_writes_meta_json(fake_config: Path) -> None:
    """meta.json captures HAEO + HA versions, timestamp, and label."""
    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        label="pre-migration",
        now=FIXED_DT,
    )

    meta = json.loads((info.snapshot_dir / "meta.json").read_text())
    assert meta == {
        "haeo_version": "0.4.0rc1",
        "ha_version": "2026.1.1",
        "created_at": "2026-04-22T20:41:30+00:00",
        "label": "pre-migration",
    }


def test_save_meta_label_is_null_when_omitted(fake_config: Path) -> None:
    """meta.json label is null when no label supplied."""
    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        now=FIXED_DT,
    )

    meta = json.loads((info.snapshot_dir / "meta.json").read_text())
    assert meta["label"] is None


def test_save_with_label_appends_to_id(fake_config: Path) -> None:
    """--label foo turns the id into <haeo>__<ts>__foo."""
    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        label="pre-migration",
        now=FIXED_DT,
    )

    assert info.snapshot_dir.name == f"{FIXED_ID}__pre-migration"


def test_save_collision_raises(fake_config: Path) -> None:
    """Two saves with the same id raise SnapshotError."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=FIXED_DT)

    with pytest.raises(snapshot.SnapshotError, match="already exists"):
        snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=FIXED_DT)


def test_save_missing_storage_raises(tmp_path: Path) -> None:
    """Saving with no .storage dir raises a clear error."""
    config = tmp_path / "config"
    config.mkdir()
    (config / ".HA_VERSION").write_text("2026.1.1")

    with pytest.raises(snapshot.SnapshotError, match=r"\.storage"):
        snapshot.create_snapshot(config_dir=config, haeo_version="0.4.0rc1", now=FIXED_DT)


def test_list_snapshots_newest_first(fake_config: Path) -> None:
    """list_snapshots returns snapshots sorted by created_at descending."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=datetime(2026, 1, 1, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=datetime(2026, 4, 22, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.5", now=datetime(2026, 2, 15, tzinfo=UTC))

    listed = snapshot.list_snapshots(config_dir=fake_config)

    assert [s.meta["haeo_version"] for s in listed] == ["0.4.0rc1", "0.3.5", "0.3.0"]


def test_list_returns_empty_when_no_snapshots(fake_config: Path) -> None:
    """No snapshots dir means empty list, not error."""
    assert snapshot.list_snapshots(config_dir=fake_config) == []


def test_restore_replaces_storage(fake_config: Path) -> None:
    """Restore overwrites .storage with the snapshot contents."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)
    (fake_config / ".storage" / "core.config_entries").write_text('{"entries": ["new"]}')

    snapshot.restore_snapshot(
        config_dir=fake_config,
        query=info.snapshot_dir.name,
        haeo_version="0.4.0rc1",
        backup=False,
    )

    assert (fake_config / ".storage" / "core.config_entries").read_text() == '{"entries": []}'


def test_restore_removes_files_not_in_snapshot(fake_config: Path) -> None:
    """Restore replaces, not merges: extra files in current .storage are gone."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)
    (fake_config / ".storage" / "extra_file").write_text("added later")

    snapshot.restore_snapshot(
        config_dir=fake_config,
        query=info.snapshot_dir.name,
        haeo_version="0.4.0rc1",
        backup=False,
    )

    assert not (fake_config / ".storage" / "extra_file").exists()


def test_restore_replaces_ha_version(fake_config: Path) -> None:
    """Restore writes the snapshot's .HA_VERSION to the config dir."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)
    (fake_config / ".HA_VERSION").write_text("2026.5.1")

    snapshot.restore_snapshot(
        config_dir=fake_config,
        query=info.snapshot_dir.name,
        haeo_version="0.4.0rc1",
        backup=False,
    )

    assert (fake_config / ".HA_VERSION").read_text() == "2026.1.1"


def test_restore_creates_pre_restore_backup(fake_config: Path) -> None:
    """Default restore saves a labeled backup of current state first."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)
    (fake_config / ".storage" / "core.config_entries").write_text('{"entries": ["modified"]}')

    snapshot.restore_snapshot(
        config_dir=fake_config,
        query=info.snapshot_dir.name,
        haeo_version="0.4.0rc1",
        now=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
    )

    snapshots = snapshot.list_snapshots(config_dir=fake_config)
    pre = [s for s in snapshots if s.meta.get("label") == "pre-restore"]
    assert len(pre) == 1
    assert (pre[0].snapshot_dir / "storage" / "core.config_entries").read_text() == '{"entries": ["modified"]}'


def test_resolve_latest(fake_config: Path) -> None:
    """`latest` returns the newest snapshot."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=datetime(2026, 1, 1, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=datetime(2026, 4, 22, tzinfo=UTC))

    resolved = snapshot.resolve_snapshot(config_dir=fake_config, query="latest")

    assert resolved.name.startswith("0.4.0rc1__")


def test_resolve_by_label(fake_config: Path) -> None:
    """A query that matches a snapshot label resolves to that snapshot."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", label="alpha", now=FIXED_DT)

    resolved = snapshot.resolve_snapshot(config_dir=fake_config, query="alpha")

    assert resolved.name.endswith("__alpha")


def test_resolve_by_unique_prefix(fake_config: Path) -> None:
    """A unique id prefix resolves to the matching snapshot."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)

    resolved = snapshot.resolve_snapshot(config_dir=fake_config, query="0.3.0__")

    assert resolved.name == "0.3.0__20260422T204130Z"


def test_resolve_ambiguous_prefix_raises(fake_config: Path) -> None:
    """A prefix matching multiple snapshots raises SnapshotError."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=datetime(2026, 1, 1, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.5", now=datetime(2026, 2, 1, tzinfo=UTC))

    with pytest.raises(snapshot.SnapshotError, match="matches multiple"):
        snapshot.resolve_snapshot(config_dir=fake_config, query="0.3")


def test_resolve_no_match_raises(fake_config: Path) -> None:
    """An unmatched query raises SnapshotError."""
    with pytest.raises(snapshot.SnapshotError, match="no snapshot"):
        snapshot.resolve_snapshot(config_dir=fake_config, query="nope")


def test_restore_atomic_rollback(fake_config: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure mid-restore leaves .storage and .HA_VERSION untouched."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=FIXED_DT)
    (fake_config / ".storage" / "core.config_entries").write_text('{"entries": ["modified"]}')

    def boom(_src: Path, _dst: Path) -> None:
        msg = "simulated failure"
        raise OSError(msg)

    monkeypatch.setattr(snapshot, "_atomic_replace", boom)

    with pytest.raises(OSError, match="simulated"):
        snapshot.restore_snapshot(
            config_dir=fake_config,
            query=info.snapshot_dir.name,
            haeo_version="0.4.0rc1",
            backup=False,
        )

    assert (fake_config / ".storage" / "core.config_entries").read_text() == '{"entries": ["modified"]}'
    assert (fake_config / ".HA_VERSION").read_text() == "2026.1.1"


def test_safety_refuses_when_pid_file_exists(fake_config: Path) -> None:
    """Save refuses when home-assistant.pid is present."""
    (fake_config / "home-assistant.pid").write_text("123")

    with pytest.raises(snapshot.SnapshotError, match="running"):
        snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=FIXED_DT)


def test_safety_force_bypasses_pid_check(fake_config: Path) -> None:
    """--force bypasses the running-HA refusal."""
    (fake_config / "home-assistant.pid").write_text("123")

    info = snapshot.create_snapshot(
        config_dir=fake_config,
        haeo_version="0.4.0rc1",
        now=FIXED_DT,
        force=True,
    )

    assert info.snapshot_dir.is_dir()


def test_delete_removes_snapshot(fake_config: Path) -> None:
    """delete_snapshot removes the matching directory."""
    info = snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.4.0rc1", now=FIXED_DT)

    removed = snapshot.delete_snapshot(config_dir=fake_config, query=info.snapshot_dir.name)

    assert not info.snapshot_dir.exists()
    assert removed == [info.snapshot_dir.name]


def test_delete_ambiguous_refuses_without_force(fake_config: Path) -> None:
    """A prefix matching multiple snapshots refuses delete unless --force."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=datetime(2026, 1, 1, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.5", now=datetime(2026, 2, 1, tzinfo=UTC))

    with pytest.raises(snapshot.SnapshotError, match="matches multiple"):
        snapshot.delete_snapshot(config_dir=fake_config, query="0.3")


def test_delete_ambiguous_with_force_removes_all(fake_config: Path) -> None:
    """Delete with --force removes all snapshots matching the prefix."""
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.0", now=datetime(2026, 1, 1, tzinfo=UTC))
    snapshot.create_snapshot(config_dir=fake_config, haeo_version="0.3.5", now=datetime(2026, 2, 1, tzinfo=UTC))

    removed = snapshot.delete_snapshot(config_dir=fake_config, query="0.3", force=True)

    assert sorted(removed) == ["0.3.0__20260101T000000Z", "0.3.5__20260201T000000Z"]
    assert list((fake_config / ".snapshots").iterdir()) == []


def test_main_save_and_list_round_trip(fake_config: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """End-to-end: invoke main() to save, then list."""
    rc_save = snapshot.main(
        ["save", "--label", "demo", "--config-dir", str(fake_config), "--haeo-version", "0.4.0rc1"],
    )
    assert rc_save == 0

    capsys.readouterr()

    rc_list = snapshot.main(["list", "--config-dir", str(fake_config)])
    assert rc_list == 0

    output = capsys.readouterr().out
    assert "0.4.0rc1" in output
    assert "demo" in output


def test_main_restore_round_trip(fake_config: Path) -> None:
    """End-to-end: save, mutate, restore via the CLI."""
    snapshot.main(
        ["save", "--config-dir", str(fake_config), "--haeo-version", "0.3.0"],
    )
    (fake_config / ".storage" / "core.config_entries").write_text('{"entries": ["mutated"]}')

    rc = snapshot.main(
        [
            "restore",
            "latest",
            "--config-dir",
            str(fake_config),
            "--haeo-version",
            "0.4.0rc1",
            "--no-backup",
        ],
    )

    assert rc == 0
    assert (fake_config / ".storage" / "core.config_entries").read_text() == '{"entries": []}'
