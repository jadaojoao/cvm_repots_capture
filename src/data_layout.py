from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.settings import AppSettings, get_settings


@dataclass(frozen=True)
class DataLayoutSyncEntry:
    source: Path
    target: Path
    bucket: str
    source_scope: str
    status: str


def infer_canonical_bucket(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "raw"
    if suffix == ".csv":
        return "processed"
    return None


def find_loose_input_files(settings: AppSettings | None = None) -> tuple[Path, ...]:
    settings = settings or get_settings()
    input_dir = settings.paths.input_dir
    if not input_dir.exists():
        return ()

    files = []
    for child in input_dir.iterdir():
        if not child.is_file():
            continue
        if infer_canonical_bucket(child) is None:
            continue
        files.append(child)
    return tuple(sorted(files))


def _iter_legacy_candidates(settings: AppSettings) -> list[tuple[Path, str, str]]:
    candidates: list[tuple[Path, str, str]] = []
    seen: set[Path] = set()

    for loose_file in find_loose_input_files(settings):
        if loose_file in seen:
            continue
        bucket = infer_canonical_bucket(loose_file)
        if bucket is None:
            continue
        candidates.append((loose_file, bucket, "input-root"))
        seen.add(loose_file)

    for legacy_root in settings.paths.legacy_data_paths:
        if not legacy_root.exists():
            continue

        if legacy_root.is_dir() and legacy_root.name in {"raw", "processed"}:
            default_bucket = legacy_root.name
            for child in legacy_root.rglob("*"):
                if not child.is_file():
                    continue
                if child in seen:
                    continue
                bucket = infer_canonical_bucket(child) or default_bucket
                if bucket not in {"raw", "processed"}:
                    continue
                candidates.append((child, bucket, legacy_root.name))
                seen.add(child)
            continue

        raw_root = legacy_root / "raw"
        processed_root = legacy_root / "processed"
        if raw_root.exists():
            for child in raw_root.rglob("*"):
                if not child.is_file():
                    continue
                if child in seen:
                    continue
                bucket = infer_canonical_bucket(child) or "raw"
                if bucket != "raw":
                    continue
                candidates.append((child, bucket, f"{legacy_root.name}/raw"))
                seen.add(child)
        if processed_root.exists():
            for child in processed_root.rglob("*"):
                if not child.is_file():
                    continue
                if child in seen:
                    continue
                bucket = infer_canonical_bucket(child) or "processed"
                if bucket != "processed":
                    continue
                candidates.append((child, bucket, f"{legacy_root.name}/processed"))
                seen.add(child)

    return candidates


def build_data_layout_sync_plan(settings: AppSettings | None = None) -> tuple[DataLayoutSyncEntry, ...]:
    settings = settings or get_settings()
    entries: list[DataLayoutSyncEntry] = []

    for source, bucket, source_scope in _iter_legacy_candidates(settings):
        if bucket == "raw":
            target = settings.paths.raw_dir / source.name
        else:
            target = settings.paths.processed_dir / source.name

        status = "already_present" if target.exists() else "copy_missing"
        entries.append(
            DataLayoutSyncEntry(
                source=source,
                target=target,
                bucket=bucket,
                source_scope=source_scope,
                status=status,
            )
        )

    return tuple(
        sorted(
            entries,
            key=lambda row: (row.status, row.bucket, str(row.source)),
        )
    )


def has_pending_noncanonical_data(settings: AppSettings | None = None) -> bool:
    return any(entry.status == "copy_missing" for entry in build_data_layout_sync_plan(settings))
