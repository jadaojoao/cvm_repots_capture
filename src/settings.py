from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return int(default)
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return float(default)
    return float(raw)


def _default_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _resolve_shared_repo_root_for_worktree(project_root: Path) -> Path | None:
    lane_dir = project_root.parent
    worktrees_dir = lane_dir.parent
    claude_dir = worktrees_dir.parent
    repo_root = claude_dir.parent

    if worktrees_dir.name != "worktrees" or claude_dir.name != ".claude":
        return None
    return repo_root.resolve()


def _resolve_path(base_dir: Path, raw_path: str | None, fallback: Path) -> Path:
    if not raw_path:
        return fallback
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def _prefer_existing_shared_path(
    local_path: Path,
    shared_repo_root: Path | None,
    relative_path: Path,
) -> Path:
    if local_path.exists() or shared_repo_root is None:
        return local_path

    shared_candidate = (shared_repo_root / relative_path).resolve()
    if shared_candidate.exists():
        return shared_candidate
    return local_path


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    data_dir: Path
    input_dir: Path
    raw_dir: Path
    processed_dir: Path
    output_dir: Path
    reports_dir: Path
    logs_dir: Path
    cache_dir: Path
    metadata_dir: Path
    db_dir: Path
    db_path: Path
    canonical_accounts_path: Path
    account_dictionary_path: Path
    active_universe_cache_path: Path
    base_health_snapshot_path: Path
    processed_presence_index_path: Path
    yfinance_cache_path: Path
    legacy_data_paths: tuple[Path, ...]

    @property
    def sqlite_url(self) -> str:
        return f"sqlite:///{self.db_path}"


@dataclass(frozen=True)
class AppSettings:
    paths: AppPaths
    database_url: str | None
    cvm_base_url: str
    default_report_type: str
    company_list_timeout: int
    download_timeout: int
    max_excel_lock_retries: int
    company_db_max_retries: int
    company_db_retry_backoff_seconds: float
    updater_skip_complete: bool
    updater_fast_lane: bool
    updater_force_refresh: bool


def build_settings(project_root: Path | None = None) -> AppSettings:
    resolved_root = Path(project_root).resolve() if project_root else _default_project_root()
    shared_repo_root = _resolve_shared_repo_root_for_worktree(resolved_root)

    data_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_DATA_DIR"),
        resolved_root / "data",
    )
    input_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_INPUT_DIR"),
        data_dir / "input",
    )
    output_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_OUTPUT_DIR"),
        resolved_root / "output",
    )
    reports_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_REPORTS_DIR"),
        output_dir / "reports",
    )
    logs_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_LOG_DIR"),
        output_dir / "logs",
    )
    cache_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_CACHE_DIR"),
        data_dir / "cache",
    )
    metadata_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_METADATA_DIR"),
        data_dir / "metadata",
    )
    db_dir = _resolve_path(
        resolved_root,
        os.getenv("CVM_DB_DIR"),
        data_dir / "db",
    )
    db_path = _resolve_path(
        resolved_root,
        os.getenv("SQLITE_PATH"),
        db_dir / "cvm_financials.db",
    )
    db_path = _prefer_existing_shared_path(
        db_path,
        shared_repo_root,
        Path("data/db/cvm_financials.db"),
    )
    canonical_accounts_path = _prefer_existing_shared_path(
        _resolve_path(
            resolved_root,
            os.getenv("CVM_CANONICAL_ACCOUNTS_PATH"),
            resolved_root / "config" / "canonical_accounts.csv",
        ),
        shared_repo_root,
        Path("config/canonical_accounts.csv"),
    )
    account_dictionary_path = _prefer_existing_shared_path(
        _resolve_path(
            resolved_root,
            os.getenv("CVM_ACCOUNT_DICTIONARY_PATH"),
            data_dir / "cvm_account_dictionary.csv",
        ),
        shared_repo_root,
        Path("data/cvm_account_dictionary.csv"),
    )

    paths = AppPaths(
        project_root=resolved_root,
        data_dir=data_dir,
        input_dir=input_dir,
        raw_dir=input_dir / "raw",
        processed_dir=input_dir / "processed",
        output_dir=output_dir,
        reports_dir=reports_dir,
        logs_dir=logs_dir,
        cache_dir=cache_dir,
        metadata_dir=metadata_dir,
        db_dir=db_dir,
        db_path=db_path,
        canonical_accounts_path=canonical_accounts_path,
        account_dictionary_path=account_dictionary_path,
        active_universe_cache_path=cache_dir / "active_universe_cache.json",
        base_health_snapshot_path=cache_dir / "base_health_snapshot.json",
        processed_presence_index_path=cache_dir / "processed_presence_index.json",
        yfinance_cache_path=cache_dir / "yfinance_cache.json",
        legacy_data_paths=(
            data_dir / "raw",
            data_dir / "processed",
            data_dir / "cvm_raw",
        ),
    )

    database_url = os.getenv("DATABASE_URL") or None

    return AppSettings(
        paths=paths,
        database_url=database_url,
        cvm_base_url=os.getenv(
            "CVM_BASE_URL",
            "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC",
        ),
        default_report_type=os.getenv("CVM_DEFAULT_REPORT_TYPE", "consolidated"),
        company_list_timeout=_env_int("CVM_COMPANY_LIST_TIMEOUT", 30),
        download_timeout=_env_int("CVM_DOWNLOAD_TIMEOUT", 60),
        max_excel_lock_retries=_env_int("CVM_MAX_EXCEL_LOCK_RETRIES", 10),
        company_db_max_retries=_env_int("CVM_COMPANY_DB_MAX_RETRIES", 3),
        company_db_retry_backoff_seconds=_env_float("CVM_COMPANY_DB_RETRY_BACKOFF_SECONDS", 1.2),
        updater_skip_complete=_env_bool("UPDATER_SKIP_COMPLETE", True),
        updater_fast_lane=_env_bool("UPDATER_FAST_LANE", True),
        updater_force_refresh=_env_bool("UPDATER_FORCE_REFRESH", False),
    )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    return build_settings()
