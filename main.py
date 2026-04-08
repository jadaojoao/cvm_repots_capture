from __future__ import annotations

import argparse
import sys

from src.contracts import RefreshPolicy, RefreshRequest
from src.refresh_service import HeadlessRefreshService
from src.settings import get_settings
from src.startup import collect_startup_report, format_startup_report

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(description="CVM Financial Data Scraper")
    parser.add_argument("--companies", nargs="+", required=True, help="List of company names or CVM codes")
    parser.add_argument("--start_year", type=int, required=True, help="Start year (YYYY)")
    parser.add_argument("--end_year", type=int, required=True, help="End year (YYYY)")
    parser.add_argument(
        "--type",
        choices=["consolidated", "individual"],
        default=settings.default_report_type,
        help="Report type",
    )
    parser.add_argument(
        "--output_dir",
        default=str(settings.paths.reports_dir),
        help="Directory for output files",
    )
    parser.add_argument(
        "--data_dir",
        default=str(settings.paths.input_dir),
        help="Directory for data storage",
    )
    parser.add_argument("--skip_complete", action="store_true", help="Skip company-years already completos")
    parser.add_argument("--fast_lane", action="store_true", help="Prioritize only recent pending years")
    parser.add_argument("--force_refresh", action="store_true", help="Ignore planner shortcuts and force the requested range")

    args = parser.parse_args()
    report = collect_startup_report(
        settings,
        require_database=False,
        require_canonical_accounts=True,
    )
    if report.issues:
        print(format_startup_report(report))

    print(f"Initializing headless refresh for {args.companies}...")
    service = HeadlessRefreshService(settings=settings)
    request = RefreshRequest(
        companies=tuple(args.companies),
        start_year=args.start_year,
        end_year=args.end_year,
        report_type=args.type,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        policy=RefreshPolicy(
            skip_complete_company_years=bool(args.skip_complete),
            enable_fast_lane=bool(args.fast_lane),
            force_refresh=bool(args.force_refresh),
        ),
    )
    result = service.execute(request)
    print(
        f"Refresh finished: success={result.success_count}, "
        f"no_data={result.no_data_count}, error={result.error_count}, "
        f"synced={result.synced_companies}, cancelled={result.cancelled}"
    )
    if result.error_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
