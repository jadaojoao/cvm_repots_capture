from __future__ import annotations

from apps.api.app.presenters import (
    present_company_info,
    present_company_search,
    present_health_snapshot,
    present_kpis,
    present_refresh_status,
    present_statement,
)
from src.contracts import (
    CompanyInfoDTO,
    CompanySearchResult,
    HealthPriority,
    HealthSnapshot,
    HealthYearCoverage,
    KPIBundle,
    RefreshStatusDTO,
    StatementMatrix,
    TabularData,
)


def test_presenters_serialize_dtos_without_raw_pandas_objects():
    company_search = present_company_search(
        [
            CompanySearchResult(
                cd_cvm=9512,
                company_name="PETROBRAS",
                ticker_b3="PETR4",
                setor_analitico="Energia",
                setor_cvm="Energia",
                anos_disponiveis=(2023, 2024),
                total_rows=30,
            )
        ]
    )[0]
    assert company_search.anos_disponiveis == [2023, 2024]

    company_info = present_company_info(
        CompanyInfoDTO(
            cd_cvm=9512,
            company_name="PETROBRAS",
            nome_comercial="Petrobras",
            cnpj="33.000.167/0001-01",
            setor_cvm="Energia",
            setor_analitico="Energia",
            company_type="comercial",
            ticker_b3="PETR4",
        )
    )
    assert company_info.company_name == "PETROBRAS"

    statement = present_statement(
        StatementMatrix(
            cd_cvm=9512,
            statement_type="DRE",
            years=(2023, 2024),
            table=TabularData(
                columns=("CD_CONTA", "2023", "2024"),
                rows=({"CD_CONTA": "3.01", "2023": 1000.0, "2024": 1100.0},),
            ),
        )
    )
    assert statement.table.columns == ["CD_CONTA", "2023", "2024"]

    kpis = present_kpis(
        KPIBundle(
            cd_cvm=9512,
            years=(2023, 2024),
            annual=TabularData(columns=("KPI_ID", "2024"), rows=({"KPI_ID": "MG_EBIT", "2024": 0.2},)),
            quarterly=TabularData(columns=("KPI_ID", "2024"), rows=({"KPI_ID": "MG_EBIT", "2024": 0.2},)),
        )
    )
    assert kpis.annual.rows[0]["KPI_ID"] == "MG_EBIT"

    refresh = present_refresh_status(
        [
            RefreshStatusDTO(
                cd_cvm=9512,
                company_name="PETROBRAS",
                source_scope="local",
                last_attempt_at="2026-04-08T08:50:00",
                last_success_at="2026-04-08T08:55:00",
                last_status="success",
                last_error=None,
                last_start_year=2023,
                last_end_year=2024,
                last_rows_inserted=30,
                updated_at="2026-04-08T08:55:00",
            )
        ]
    )[0]
    assert refresh.last_status == "success"

    health = present_health_snapshot(
        HealthSnapshot(
            generated_at="2026-04-08T09:00:00",
            start_year=2023,
            end_year=2024,
            total_cells=4,
            completed_cells=3,
            missing_cells=1,
            pct=75.0,
            health_score=82.5,
            health_status="atencao",
            eta_hours=1.5,
            throughput_per_hour=2.0,
            throughput_confidence="medium",
            per_year=(
                HealthYearCoverage(year=2023, total_companies=2, completed=2, missing=0, pct=100.0, eta_hours=0.0),
                HealthYearCoverage(year=2024, total_companies=2, completed=1, missing=1, pct=50.0, eta_hours=0.5),
            ),
            prioritized_companies=(
                HealthPriority(
                    cd_cvm=9512,
                    company_name="PETROBRAS",
                    risk_level="medio",
                    priority_score=125,
                    missing_years_count=1,
                    gap_to_leader_years=1,
                    years_missing=(2024,),
                    recommended_action="Atualizar ano 2024",
                    reason="Gap relevante com lider",
                ),
            ),
            raw={"generated_at": "2026-04-08T09:00:00"},
        )
    )
    assert health.per_year[0].year == 2023
    assert health.prioritized_companies[0].years_missing == [2024]
