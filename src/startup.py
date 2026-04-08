from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import inspect

from src.data_layout import find_loose_input_files, has_pending_noncanonical_data
from src.db import build_engine
from src.settings import AppSettings, get_settings


@dataclass(frozen=True)
class StartupIssue:
    severity: str
    code: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class StartupReport:
    issues: tuple[StartupIssue, ...]

    @property
    def errors(self) -> tuple[StartupIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[StartupIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors


def _issue(severity: str, code: str, message: str, path: Path | None = None) -> StartupIssue:
    return StartupIssue(
        severity=severity,
        code=code,
        message=message,
        path=str(path) if path else None,
    )


def collect_startup_report(
    settings: AppSettings | None = None,
    *,
    require_database: bool = False,
    required_tables: Iterable[str] = (),
    require_canonical_accounts: bool = False,
    warn_on_legacy_data: bool = True,
) -> StartupReport:
    settings = settings or get_settings()
    paths = settings.paths
    issues: list[StartupIssue] = []

    executable = Path(sys.executable)
    if not executable.exists():
        issues.append(_issue("error", "python-missing", "Python executavel atual nao existe.", executable))

    project_venv = paths.project_root / ".venv"
    if project_venv.exists():
        venv_python = project_venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
        if not venv_python.exists():
            issues.append(
                _issue(
                    "warning",
                    "venv-broken",
                    "A pasta .venv existe, mas o interpretador esperado nao foi encontrado.",
                    venv_python,
                )
            )

    if require_canonical_accounts and not paths.canonical_accounts_path.exists():
        issues.append(
            _issue(
                "warning",
                "canonical-accounts-missing",
                "Arquivo de contas canonicas nao encontrado; a padronizacao ficara degradada.",
                paths.canonical_accounts_path,
            )
        )

    if warn_on_legacy_data:
        loose_input_files = find_loose_input_files(settings)
        if loose_input_files:
            issues.append(
                _issue(
                    "warning",
                    "noncanonical-input-layout",
                    "Arquivos .zip/.csv foram encontrados diretamente em data/input; o layout canonico usa data/input/raw e data/input/processed.",
                    paths.input_dir,
                )
            )

        if has_pending_noncanonical_data(settings):
            for legacy_path in paths.legacy_data_paths:
                if legacy_path.exists() and any(legacy_path.iterdir()):
                    issues.append(
                        _issue(
                            "warning",
                            "legacy-data-root",
                            "Diretorio legado contem arquivos ainda nao sincronizados com o layout canonico; use scripts/canonicalize_data_layout.py.",
                            legacy_path,
                        )
                    )
                    break

    if require_database:
        if not settings.database_url and not paths.db_path.exists():
            issues.append(
                _issue(
                    "error",
                    "database-missing",
                    "Banco local nao encontrado e DATABASE_URL nao configurada.",
                    paths.db_path,
                )
            )
        else:
            try:
                engine = build_engine(settings)
                inspector = inspect(engine)
                missing_tables = [
                    table_name
                    for table_name in required_tables
                    if not inspector.has_table(table_name)
                ]
                if missing_tables:
                    issues.append(
                        _issue(
                            "error",
                            "database-missing-tables",
                            "Tabelas obrigatorias ausentes: " + ", ".join(sorted(missing_tables)),
                            paths.db_path if not settings.database_url else None,
                        )
                    )
            except Exception as exc:
                issues.append(
                    _issue(
                        "error",
                        "database-unreachable",
                        f"Nao foi possivel validar o banco configurado: {exc}",
                        paths.db_path if not settings.database_url else None,
                    )
                )

    return StartupReport(issues=tuple(issues))


def format_startup_report(report: StartupReport) -> str:
    if not report.issues:
        return "Ambiente validado."

    lines = []
    for issue in report.issues:
        prefix = "ERRO" if issue.severity == "error" else "AVISO"
        line = f"[{prefix}] {issue.code}: {issue.message}"
        if issue.path:
            line += f" ({issue.path})"
        lines.append(line)
    return "\n".join(lines)


def ensure_startup_ready(
    settings: AppSettings | None = None,
    *,
    require_database: bool = False,
    required_tables: Iterable[str] = (),
    require_canonical_accounts: bool = False,
    warn_on_legacy_data: bool = True,
) -> StartupReport:
    report = collect_startup_report(
        settings,
        require_database=require_database,
        required_tables=required_tables,
        require_canonical_accounts=require_canonical_accounts,
        warn_on_legacy_data=warn_on_legacy_data,
    )
    if not report.ok:
        raise RuntimeError(format_startup_report(report))
    return report
