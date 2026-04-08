from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import bindparam, create_engine, inspect, text

from src.contracts import CompanyRefreshResult, RefreshRequest, RefreshResult
from src.db import build_engine
from src.observability import append_jsonl, log_event
from src.scraper import CVMScraper
from src.settings import AppSettings, get_settings


class HeadlessRefreshService:
    REQUIRED_PACKAGE_STATEMENTS = ("BPA", "BPP", "DRE", "DFC")
    FAST_LANE_RECENT_YEARS = 2
    MAX_AUTO_REPORTING_YEAR_LAG = 1

    def __init__(self, settings: AppSettings | None = None, logger: logging.Logger | None = None):
        self.settings = settings or get_settings()
        self.logger = logger or logging.getLogger(__name__)

    def _engine_for(self, db_path_override: Path | None = None):
        if db_path_override is None:
            return build_engine(self.settings)
        return create_engine(
            f"sqlite:///{Path(db_path_override).resolve()}",
            connect_args={"check_same_thread": False},
        )

    @staticmethod
    def _table_exists(engine, table_name: str) -> bool:
        return inspect(engine).has_table(table_name)

    def _load_complete_company_years(
        self,
        request: RefreshRequest,
        *,
        db_path_override: Path | None = None,
    ) -> dict[int, set[int]]:
        if request.policy.force_refresh or not request.policy.skip_complete_company_years:
            return {}

        company_codes = [
            int(code)
            for code in request.companies
            if str(code).isdigit()
        ]
        if not company_codes:
            return {}

        engine = self._engine_for(db_path_override)
        if not self._table_exists(engine, "financial_reports"):
            return {}

        query = text(
            """
            SELECT
                "CD_CVM" AS cd_cvm,
                "REPORT_YEAR" AS report_year,
                COUNT(DISTINCT "STATEMENT_TYPE") AS stmt_count
            FROM financial_reports
            WHERE "CD_CVM" IN :company_codes
              AND "REPORT_YEAR" BETWEEN :start_year AND :end_year
              AND "STATEMENT_TYPE" IN :statement_types
            GROUP BY "CD_CVM", "REPORT_YEAR"
            HAVING COUNT(DISTINCT "STATEMENT_TYPE") >= :required_count
            """
        ).bindparams(
            bindparam("company_codes", expanding=True),
            bindparam("statement_types", expanding=True),
        )

        params = {
            "company_codes": company_codes,
            "start_year": int(request.start_year),
            "end_year": int(request.end_year),
            "statement_types": list(self.REQUIRED_PACKAGE_STATEMENTS),
            "required_count": len(self.REQUIRED_PACKAGE_STATEMENTS),
        }
        completed_map: dict[int, set[int]] = {}
        with engine.connect() as conn:
            for row in conn.execute(query, params).mappings():
                cd_cvm = int(row["cd_cvm"])
                report_year = int(row["report_year"])
                completed_map.setdefault(cd_cvm, set()).add(report_year)
        return completed_map

    def build_company_year_plan(
        self,
        request: RefreshRequest,
        *,
        db_path_override: Path | None = None,
    ) -> tuple[list[str], dict[int, list[int]], dict[str, int]]:
        raw_years_scope = list(range(int(request.start_year), int(request.end_year) + 1))
        max_auto_year = datetime.now().year - self.MAX_AUTO_REPORTING_YEAR_LAG
        years_scope = [int(year) for year in raw_years_scope if int(year) <= int(max_auto_year)]
        if not years_scope:
            return [], {}, {
                "requested_company_years": 0,
                "planned_company_years": 0,
                "skipped_complete_company_years": 0,
                "deferred_fast_lane_company_years": 0,
                "planned_companies": 0,
                "skipped_companies_all_complete": 0,
                "dropped_future_years": int(len(raw_years_scope)),
            }

        unique_company_codes: list[int] = []
        seen_codes: set[int] = set()
        for raw_code in request.companies:
            if not str(raw_code).isdigit():
                continue
            code = int(raw_code)
            if code in seen_codes:
                continue
            seen_codes.add(code)
            unique_company_codes.append(code)

        completed_map = self._load_complete_company_years(request, db_path_override=db_path_override)

        recent_floor_year = datetime.now().year - (self.FAST_LANE_RECENT_YEARS - 1)
        planned_companies: list[str] = []
        company_year_overrides: dict[int, list[int]] = {}
        skipped_complete_company_years = 0
        deferred_fast_lane_company_years = 0
        skipped_companies_all_complete = 0

        for code in unique_company_codes:
            completed_years = completed_map.get(code, set())
            years_needed = [int(year) for year in years_scope if int(year) not in completed_years]
            skipped_complete_company_years += len(years_scope) - len(years_needed)

            if not years_needed:
                skipped_companies_all_complete += 1
                continue

            years_to_run = years_needed
            if request.policy.enable_fast_lane and not request.policy.force_refresh:
                recent_years = [int(year) for year in years_needed if int(year) >= int(recent_floor_year)]
                if recent_years:
                    deferred_fast_lane_company_years += len(years_needed) - len(recent_years)
                    years_to_run = recent_years

            if not years_to_run:
                skipped_companies_all_complete += 1
                continue

            planned_companies.append(str(code))
            company_year_overrides[int(code)] = sorted(set(int(year) for year in years_to_run))

        stats = {
            "requested_company_years": int(len(unique_company_codes) * len(raw_years_scope)),
            "planned_company_years": int(sum(len(years) for years in company_year_overrides.values())),
            "skipped_complete_company_years": int(skipped_complete_company_years),
            "deferred_fast_lane_company_years": int(deferred_fast_lane_company_years),
            "planned_companies": int(len(planned_companies)),
            "skipped_companies_all_complete": int(skipped_companies_all_complete),
            "dropped_future_years": int(len(raw_years_scope) - len(years_scope)),
        }
        return planned_companies, company_year_overrides, stats

    def _ensure_refresh_status_table(self, conn) -> None:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS company_refresh_status (
                    cd_cvm INTEGER PRIMARY KEY,
                    company_name TEXT,
                    source_scope TEXT NOT NULL DEFAULT 'local',
                    last_attempt_at TEXT,
                    last_success_at TEXT,
                    last_status TEXT,
                    last_error TEXT,
                    last_start_year INTEGER,
                    last_end_year INTEGER,
                    last_rows_inserted INTEGER,
                    updated_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_crs_status
                ON company_refresh_status(last_status)
                """
            )
        )

    @staticmethod
    def _count_rows_for_company_years(conn, cd_cvm: int, start_year: int, end_year: int) -> int:
        row = conn.execute(
            text(
                """
                SELECT COUNT(*) AS total
                FROM financial_reports
                WHERE "CD_CVM" = :cd_cvm
                  AND "REPORT_YEAR" BETWEEN :start_year AND :end_year
                """
            ),
            {
                "cd_cvm": int(cd_cvm),
                "start_year": int(start_year),
                "end_year": int(end_year),
            },
        ).scalar()
        return int(row or 0)

    @staticmethod
    def _touch_company_updated_at(conn, cd_cvm: int, company_name: str, updated_at: str) -> None:
        conn.execute(
            text(
                """
                UPDATE companies
                SET company_name = COALESCE(NULLIF(:company_name, ''), company_name),
                    updated_at = :updated_at
                WHERE cd_cvm = :cd_cvm
                """
            ),
            {
                "cd_cvm": int(cd_cvm),
                "company_name": str(company_name),
                "updated_at": str(updated_at),
            },
        )

    def sync_refresh_status(
        self,
        request: RefreshRequest,
        companies: tuple[CompanyRefreshResult, ...],
        *,
        db_path_override: Path | None = None,
    ) -> int:
        if not companies:
            return 0

        engine = self._engine_for(db_path_override)
        companies_table_exists = self._table_exists(engine, "companies")
        now_iso = datetime.now().replace(microsecond=0).isoformat()
        updated = 0

        with engine.begin() as conn:
            self._ensure_refresh_status_table(conn)
            for result in companies:
                status = str(result.status or "error").strip().lower()
                rows_in_range = int(result.rows_inserted or 0)
                if status == "success" and rows_in_range <= 0:
                    rows_in_range = self._count_rows_for_company_years(
                        conn=conn,
                        cd_cvm=result.cvm_code,
                        start_year=request.start_year,
                        end_year=request.end_year,
                    )

                error_message = result.error
                if status == "success":
                    error_message = None
                elif not error_message:
                    error_message = f"Status={status}"

                conn.execute(
                    text(
                        """
                        INSERT INTO company_refresh_status (
                            cd_cvm, company_name, source_scope,
                            last_attempt_at, last_success_at, last_status, last_error,
                            last_start_year, last_end_year, last_rows_inserted, updated_at
                        ) VALUES (
                            :cd_cvm, :company_name, :source_scope,
                            :last_attempt_at, :last_success_at, :last_status, :last_error,
                            :last_start_year, :last_end_year, :last_rows_inserted, :updated_at
                        )
                        ON CONFLICT(cd_cvm) DO UPDATE SET
                            company_name = excluded.company_name,
                            source_scope = excluded.source_scope,
                            last_attempt_at = excluded.last_attempt_at,
                            last_success_at = COALESCE(excluded.last_success_at, company_refresh_status.last_success_at),
                            last_status = excluded.last_status,
                            last_error = excluded.last_error,
                            last_start_year = excluded.last_start_year,
                            last_end_year = excluded.last_end_year,
                            last_rows_inserted = CASE
                                WHEN excluded.last_status = 'success'
                                THEN excluded.last_rows_inserted
                                ELSE company_refresh_status.last_rows_inserted
                            END,
                            updated_at = excluded.updated_at
                        """
                    ),
                    {
                        "cd_cvm": int(result.cvm_code),
                        "company_name": result.company_name,
                        "source_scope": "local",
                        "last_attempt_at": now_iso,
                        "last_success_at": now_iso if status == "success" else None,
                        "last_status": status,
                        "last_error": error_message,
                        "last_start_year": int(request.start_year),
                        "last_end_year": int(request.end_year),
                        "last_rows_inserted": int(rows_in_range),
                        "updated_at": now_iso,
                    },
                )
                if companies_table_exists and status == "success":
                    self._touch_company_updated_at(
                        conn=conn,
                        cd_cvm=result.cvm_code,
                        company_name=result.company_name,
                        updated_at=now_iso,
                    )
                updated += 1
        return updated

    def _persist_refresh_log(self, result: RefreshResult) -> None:
        log_path = self.settings.paths.logs_dir / "refresh_runs.jsonl"
        append_jsonl(log_path, result.to_dict())

    def execute(
        self,
        request: RefreshRequest,
        *,
        progress_callback: Callable[[int, int, str], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> RefreshResult:
        planned_companies, company_year_overrides, planning_stats = self.build_company_year_plan(request)
        log_event(
            self.logger,
            "refresh-plan",
            start_year=request.start_year,
            end_year=request.end_year,
            companies=len(request.companies),
            planned_companies=len(planned_companies),
            planned_company_years=planning_stats["planned_company_years"],
            skipped_complete_company_years=planning_stats["skipped_complete_company_years"],
            deferred_fast_lane_company_years=planning_stats["deferred_fast_lane_company_years"],
        )

        if not planned_companies:
            result = RefreshResult(
                request=request,
                companies=(),
                planning_stats=planning_stats,
                synced_companies=0,
                cancelled=False,
            )
            self._persist_refresh_log(result)
            return result

        cancelled_state = {"value": False}

        def _should_cancel() -> bool:
            if should_cancel is None:
                return False
            cancelled = bool(should_cancel())
            if cancelled:
                cancelled_state["value"] = True
            return cancelled

        scraper = CVMScraper(
            data_dir=request.data_dir or str(self.settings.paths.input_dir),
            output_dir=request.output_dir or str(self.settings.paths.reports_dir),
            report_type=request.report_type,
            max_workers=request.max_workers,
            settings=self.settings,
        )
        payload = scraper.run(
            companies=planned_companies,
            start_year=request.start_year,
            end_year=request.end_year,
            company_year_overrides=company_year_overrides,
            progress_callback=progress_callback,
            should_cancel=_should_cancel,
        )
        companies = tuple(
            CompanyRefreshResult.from_payload(raw_payload)
            for raw_payload in payload.values()
        )
        synced_companies = self.sync_refresh_status(request, companies)
        result = RefreshResult(
            request=request,
            companies=companies,
            planning_stats=planning_stats,
            synced_companies=synced_companies,
            cancelled=bool(cancelled_state["value"]),
        )
        self._persist_refresh_log(result)
        log_event(
            self.logger,
            "refresh-result",
            success_count=result.success_count,
            no_data_count=result.no_data_count,
            error_count=result.error_count,
            cancelled=result.cancelled,
            synced_companies=result.synced_companies,
        )
        return result
