# -*- coding: utf-8 -*-
from __future__ import annotations

from src.data_layout import build_data_layout_sync_plan, find_loose_input_files
from src.settings import build_settings


def test_find_loose_input_files_detects_top_level_zip_and_csv(tmp_path):
    settings = build_settings(project_root=tmp_path)
    settings.paths.input_dir.mkdir(parents=True, exist_ok=True)
    zip_file = settings.paths.input_dir / "dfp_cia_aberta_2025.zip"
    csv_file = settings.paths.input_dir / "itr_cia_aberta_BPA_con_2025.csv"
    zip_file.write_text("zip", encoding="utf-8")
    csv_file.write_text("csv", encoding="utf-8")

    files = find_loose_input_files(settings)

    assert set(files) == {csv_file, zip_file}


def test_build_data_layout_sync_plan_marks_copy_and_already_present(tmp_path):
    settings = build_settings(project_root=tmp_path)
    legacy_root = settings.paths.project_root / "data" / "cvm_raw"
    (legacy_root / "raw").mkdir(parents=True, exist_ok=True)
    (legacy_root / "processed").mkdir(parents=True, exist_ok=True)

    raw_source = legacy_root / "raw" / "dfp_cia_aberta_2025.zip"
    processed_source = legacy_root / "processed" / "itr_cia_aberta_BPA_con_2025.csv"
    raw_source.write_text("zip", encoding="utf-8")
    processed_source.write_text("csv", encoding="utf-8")

    settings.paths.raw_dir.mkdir(parents=True, exist_ok=True)
    existing_target = settings.paths.raw_dir / raw_source.name
    existing_target.write_text("zip", encoding="utf-8")

    plan = build_data_layout_sync_plan(settings)
    by_source = {entry.source: entry for entry in plan}

    assert by_source[raw_source].status == "already_present"
    assert by_source[raw_source].bucket == "raw"
    assert by_source[processed_source].status == "copy_missing"
    assert by_source[processed_source].target == settings.paths.processed_dir / processed_source.name
