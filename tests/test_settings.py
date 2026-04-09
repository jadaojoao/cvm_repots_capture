# -*- coding: utf-8 -*-
from __future__ import annotations

from src.settings import build_settings


def test_build_settings_prefers_shared_runtime_files_inside_task_worktree(tmp_path):
    repo_root = tmp_path / "repo"
    worktree_root = repo_root / ".claude" / "worktrees" / "backend" / "33-postgres-contract-hardening"
    shared_db_path = repo_root / "data" / "db" / "cvm_financials.db"
    # canonical_accounts.csv agora vive em config/ (nao em data/)
    shared_canonical_path = repo_root / "config" / "canonical_accounts.csv"
    shared_dictionary_path = repo_root / "data" / "cvm_account_dictionary.csv"

    worktree_root.mkdir(parents=True, exist_ok=True)
    shared_db_path.parent.mkdir(parents=True, exist_ok=True)
    shared_db_path.touch()
    shared_canonical_path.parent.mkdir(parents=True, exist_ok=True)
    shared_canonical_path.write_text("CD_CONTA,STANDARD_NAME\n1,ATIVO\n", encoding="utf-8")
    shared_dictionary_path.write_text("CD_CONTA,STANDARD_NAME\n1,ATIVO\n", encoding="utf-8")

    settings = build_settings(project_root=worktree_root)

    assert settings.paths.db_path == shared_db_path.resolve()
    assert settings.paths.canonical_accounts_path == shared_canonical_path.resolve()
    assert settings.paths.account_dictionary_path == shared_dictionary_path.resolve()
    assert settings.paths.cache_dir == (worktree_root / "data" / "cache").resolve()


def test_build_settings_keeps_local_runtime_files_when_worktree_has_own_copy(tmp_path):
    repo_root = tmp_path / "repo"
    worktree_root = repo_root / ".claude" / "worktrees" / "backend" / "33-postgres-contract-hardening"
    local_db_path = worktree_root / "data" / "db" / "cvm_financials.db"
    # canonical_accounts.csv agora vive em config/ (nao em data/)
    local_canonical_path = worktree_root / "config" / "canonical_accounts.csv"
    local_dictionary_path = worktree_root / "data" / "cvm_account_dictionary.csv"

    local_db_path.parent.mkdir(parents=True, exist_ok=True)
    local_db_path.touch()
    local_canonical_path.parent.mkdir(parents=True, exist_ok=True)
    local_canonical_path.write_text("CD_CONTA,STANDARD_NAME\n1,ATIVO\n", encoding="utf-8")
    local_dictionary_path.write_text("CD_CONTA,STANDARD_NAME\n1,ATIVO\n", encoding="utf-8")

    settings = build_settings(project_root=worktree_root)

    assert settings.paths.db_path == local_db_path.resolve()
    assert settings.paths.canonical_accounts_path == local_canonical_path.resolve()
    assert settings.paths.account_dictionary_path == local_dictionary_path.resolve()
