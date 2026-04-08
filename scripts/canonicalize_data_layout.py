# -*- coding: utf-8 -*-
"""
Audita e sincroniza arquivos de dados para o layout canonico.

O script nunca apaga arquivos legados. Quando `--sync-missing` e usado,
ele apenas copia para `data/input/raw` ou `data/input/processed` os arquivos
que ainda nao existem no destino canonico.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.data_layout import build_data_layout_sync_plan
from src.settings import build_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audita e sincroniza o layout canonico de data/input")
    parser.add_argument("--sync-missing", action="store_true", help="Copia apenas arquivos ausentes para o layout canonico")
    parser.add_argument("--prune-duplicates", action="store_true", help="Remove arquivos soltos em data/input quando forem identicos ao destino canonico")
    parser.add_argument("--archive-input-root", action="store_true", help="Move arquivos soltos remanescentes de data/input para um arquivo legado")
    parser.add_argument("--json", action="store_true", help="Imprime a saida em JSON")
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    settings = build_settings(project_root=ROOT)
    plan = build_data_layout_sync_plan(settings)

    summary = {
        "copy_missing": sum(1 for entry in plan if entry.status == "copy_missing"),
        "already_present": sum(1 for entry in plan if entry.status == "already_present"),
        "entries": [
            {
                "source": str(entry.source),
                "target": str(entry.target),
                "bucket": entry.bucket,
                "source_scope": entry.source_scope,
                "status": entry.status,
            }
            for entry in plan
        ],
    }

    if args.sync_missing:
        for entry in plan:
            if entry.status != "copy_missing":
                continue
            entry.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(entry.source, entry.target)

    pruned = 0
    if args.prune_duplicates:
        for entry in plan:
            if entry.status != "already_present":
                continue
            if entry.source_scope != "input-root":
                continue
            if not entry.target.exists():
                continue
            if _sha256(entry.source) != _sha256(entry.target):
                continue
            entry.source.unlink()
            pruned += 1
        summary["pruned_duplicates"] = pruned

    archived = 0
    if args.archive_input_root:
        archive_dir = settings.paths.data_dir / "legacy_archives" / "input_root"
        archive_dir.mkdir(parents=True, exist_ok=True)
        for entry in plan:
            if entry.source_scope != "input-root":
                continue
            if not entry.source.exists():
                continue
            archive_target = archive_dir / entry.source.name
            if archive_target.exists():
                archive_target = archive_dir / f"{entry.source.stem}__archived{entry.source.suffix}"
            shutil.move(str(entry.source), str(archive_target))
            archived += 1
        summary["archived_input_root"] = archived

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"copy_missing={summary['copy_missing']} already_present={summary['already_present']} "
            f"pruned_duplicates={summary.get('pruned_duplicates', 0)} "
            f"archived_input_root={summary.get('archived_input_root', 0)}"
        )
        for entry in plan:
            print(
                f"[{entry.status}] {entry.source_scope} -> {entry.bucket} | "
                f"{entry.source.name} => {entry.target}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
