from __future__ import annotations

import io
import zipfile
from pathlib import Path

import openpyxl
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from src.settings import build_settings


def test_health_returns_ok_payload(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "v2-phase1"
    assert payload["database_dialect"] == client.app.state.read_service.engine.dialect.name
    assert payload["required_tables"] == ["financial_reports", "companies"]


def test_companies_empty_search_returns_paginated_directory(client: TestClient):
    response = client.get("/companies")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total_items"] == 3
    assert payload["pagination"]["page"] == 1
    assert payload["pagination"]["page_size"] == 20
    assert payload["items"][0]["company_name"] == "PETROBRAS"
    assert payload["items"][0]["anos_disponiveis"] == [2023, 2024]
    assert payload["items"][0]["sector_name"] == "Energia"
    assert payload["items"][0]["sector_slug"] == "energia"
    returned_names = [item["company_name"] for item in payload["items"]]
    assert "SEM DADOS" not in returned_names


def test_companies_search_filters_results(client: TestClient):
    response = client.get("/companies", params={"search": "vale", "page_size": 20})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total_items"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["company_name"] == "VALE"


def test_companies_pagination_respects_page_and_page_size(client: TestClient):
    response = client.get("/companies", params={"page": 2, "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"] == {
        "page": 2,
        "page_size": 1,
        "total_items": 3,
        "total_pages": 3,
        "has_next": True,
        "has_previous": True,
    }
    assert len(payload["items"]) == 1
    assert payload["items"][0]["company_name"] == "SABESP"


def test_companies_sector_filter_uses_canonical_slug(client: TestClient):
    response = client.get("/companies", params={"sector": "saneamento"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied_filters"]["sector"] == "saneamento"
    assert payload["pagination"]["total_items"] == 1
    assert payload["items"][0]["company_name"] == "SABESP"
    assert payload["items"][0]["sector_name"] == "Saneamento"


def test_companies_unknown_sector_returns_empty_page_with_stable_payload(client: TestClient):
    response = client.get("/companies", params={"sector": "setor-inexistente"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 20,
        "total_items": 0,
        "total_pages": 1,
        "has_next": False,
        "has_previous": False,
    }
    assert payload["applied_filters"] == {"search": "", "sector": "setor-inexistente"}


def test_companies_filters_returns_canonical_sector_options(client: TestClient):
    response = client.get("/companies/filters")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sectors"] == [
        {"sector_name": "Energia", "sector_slug": "energia", "company_count": 1},
        {"sector_name": "Materiais Basicos", "sector_slug": "materiais-basicos", "company_count": 1},
        {"sector_name": "Saneamento", "sector_slug": "saneamento", "company_count": 1},
    ]


def test_sectors_returns_directory_with_latest_year_and_snapshot(client: TestClient):
    response = client.get("/sectors")

    assert response.status_code == 200
    payload = response.json()
    assert [item["sector_name"] for item in payload["items"]] == [
        "Energia",
        "Materiais Basicos",
        "Saneamento",
    ]
    energia = payload["items"][0]
    assert energia["sector_slug"] == "energia"
    assert energia["company_count"] == 1
    assert energia["latest_year"] == 2024
    assert energia["snapshot"]["roe"] == pytest.approx(180.0 / 380.0)
    assert energia["snapshot"]["mg_ebit"] == pytest.approx(240.0 / 1100.0)
    assert energia["snapshot"]["mg_liq"] == pytest.approx(180.0 / 1100.0)


def test_sectors_directory_keeps_null_snapshot_metrics_when_accounts_are_partial(client: TestClient):
    response = client.get("/sectors")

    assert response.status_code == 200
    payload = response.json()
    materiais = next(item for item in payload["items"] if item["sector_slug"] == "materiais-basicos")
    assert materiais["latest_year"] == 2024
    assert materiais["snapshot"] == {"roe": None, "mg_ebit": None, "mg_liq": None}


def test_sector_detail_returns_default_latest_year_and_yearly_overview(client: TestClient):
    response = client.get("/sectors/energia")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sector_name"] == "Energia"
    assert payload["sector_slug"] == "energia"
    assert payload["company_count"] == 1
    assert payload["available_years"] == [2023, 2024]
    assert payload["selected_year"] == 2024
    assert payload["yearly_overview"] == [
        {
            "year": 2023,
            "roe": pytest.approx(150.0 / 300.0),
            "mg_ebit": pytest.approx(200.0 / 1000.0),
            "mg_liq": pytest.approx(150.0 / 1000.0),
        },
        {
            "year": 2024,
            "roe": pytest.approx(180.0 / 380.0),
            "mg_ebit": pytest.approx(240.0 / 1100.0),
            "mg_liq": pytest.approx(180.0 / 1100.0),
        },
    ]
    assert payload["companies"] == [
        {
            "cd_cvm": 9512,
            "company_name": "PETROBRAS",
            "ticker_b3": "PETR4",
            "roe": pytest.approx(180.0 / 380.0),
            "mg_ebit": pytest.approx(240.0 / 1100.0),
            "mg_liq": pytest.approx(180.0 / 1100.0),
        }
    ]


def test_sector_detail_respects_explicit_year(client: TestClient):
    response = client.get("/sectors/energia", params={"year": "2023"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_year"] == 2023
    assert payload["companies"][0]["roe"] == pytest.approx(150.0 / 300.0)


def test_sector_detail_keeps_company_row_with_null_metrics_when_accounts_are_partial(client: TestClient):
    response = client.get("/sectors/saneamento")

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_year"] == 2024
    assert payload["companies"] == [
        {
            "cd_cvm": 11223,
            "company_name": "SABESP",
            "ticker_b3": "SBSP3",
            "roe": None,
            "mg_ebit": None,
            "mg_liq": None,
        }
    ]


def test_sector_detail_returns_404_for_unknown_slug(client: TestClient):
    response = client.get("/sectors/setor-inexistente")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_sector_detail_returns_422_for_year_outside_available_range(client: TestClient):
    response = client.get("/sectors/energia", params={"year": "1990"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_detail_returns_metadata(client: TestClient):
    response = client.get("/companies/9512")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_name"] == "PETROBRAS"
    assert payload["ticker_b3"] == "PETR4"
    assert payload["sector_name"] == "Energia"
    assert payload["sector_slug"] == "energia"


def test_company_detail_uses_sector_fallback_when_analytical_sector_is_missing(client: TestClient):
    response = client.get("/companies/11223")

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_name"] == "SABESP"
    assert payload["sector_name"] == "Saneamento"
    assert payload["sector_slug"] == "saneamento"


def test_company_detail_returns_404_for_unknown_company(client: TestClient):
    response = client.get("/companies/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_company_years_returns_sorted_values(client: TestClient):
    response = client.get("/companies/9512/years")

    assert response.status_code == 200
    assert response.json() == [2023, 2024]


def test_company_years_returns_empty_list_when_company_has_no_reports(client: TestClient):
    response = client.get("/companies/77889/years")

    assert response.status_code == 200
    assert response.json() == []


def test_company_excel_export_returns_binary_workbook(client: TestClient):
    response = client.get("/companies/9512/export/excel")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'filename="PETR4_' in response.headers["content-disposition"]

    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    assert workbook.sheetnames[:4] == ["CAPA", "GERAL", "KPIs", "DRE"]


def test_company_excel_export_uses_all_available_years(client: TestClient):
    response = client.get("/companies/9512/export/excel")

    assert response.status_code == 200
    workbook = openpyxl.load_workbook(io.BytesIO(response.content))
    dre = workbook["DRE"]

    assert dre["E1"].value == "2023"
    assert dre["F1"].value == "2024"


def test_company_excel_export_returns_404_for_unknown_company(client: TestClient):
    response = client.get("/companies/999999/export/excel")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_company_excel_export_returns_422_when_company_has_no_exportable_years(client: TestClient):
    response = client.get("/companies/77889/export/excel")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_excel_batch_export_returns_zip_with_one_workbook_per_company(client: TestClient):
    response = client.get("/companies/export/excel-batch", params={"ids": "9512,4170"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/zip")
    assert 'filename="comparar_excel_lote.zip"' in response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = sorted(archive.namelist())
        assert len(names) == 2
        assert names[0].startswith("PETR4_")
        assert names[1].startswith("VALE3_")
        assert names[0].endswith(".xlsx")
        assert names[1].endswith(".xlsx")

        workbook = openpyxl.load_workbook(io.BytesIO(archive.read(names[0])))
        assert "CAPA" in workbook.sheetnames


def test_company_excel_batch_export_rejects_duplicate_ids(client: TestClient):
    response = client.get("/companies/export/excel-batch", params={"ids": "9512,9512"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_excel_batch_export_rejects_single_company(client: TestClient):
    response = client.get("/companies/export/excel-batch", params={"ids": "9512"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_excel_batch_export_returns_404_for_unknown_company(client: TestClient):
    response = client.get("/companies/export/excel-batch", params={"ids": "9512,999999"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_company_statement_returns_matrix(client: TestClient):
    response = client.get(
        "/companies/9512/statements",
        params={"stmt": "DRE", "years": "2023,2024"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["statement_type"] == "DRE"
    assert payload["years"] == [2023, 2024]
    assert "2023" in payload["table"]["columns"]
    assert "2024" in payload["table"]["columns"]


def test_company_statement_sorts_requested_years_for_stable_contract(client: TestClient):
    response = client.get(
        "/companies/9512/statements",
        params={"stmt": "DRE", "years": "2024,2023"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2023, 2024]
    assert payload["table"]["columns"][-2:] == ["2023", "2024"]


def test_company_statement_returns_empty_table_for_year_without_data(client: TestClient):
    response = client.get(
        "/companies/4170/statements",
        params={"stmt": "DRE", "years": "2023"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2023]
    assert payload["table"] == {"columns": [], "rows": []}


def test_company_statement_rejects_invalid_years(client: TestClient):
    response = client.get(
        "/companies/9512/statements",
        params={"stmt": "DRE", "years": "2024,foo"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_statement_rejects_duplicate_years(client: TestClient):
    response = client.get(
        "/companies/9512/statements",
        params={"stmt": "DRE", "years": "2024,2024"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_statement_rejects_invalid_statement(client: TestClient):
    response = client.get(
        "/companies/9512/statements",
        params={"stmt": "XYZ", "years": "2024"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_kpis_returns_annual_and_quarterly_tables(client: TestClient):
    response = client.get("/companies/9512/kpis", params={"years": "2023,2024"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cd_cvm"] == 9512
    assert payload["years"] == [2023, 2024]
    assert payload["annual"]["rows"]
    assert payload["quarterly"]["rows"]


def test_company_kpis_sort_requested_years_for_stable_contract(client: TestClient):
    response = client.get("/companies/9512/kpis", params={"years": "2024,2023"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2023, 2024]
    assert "2023" in payload["annual"]["columns"]
    assert "2024" in payload["annual"]["columns"]


def test_company_kpis_return_empty_tables_when_requested_year_has_no_data(client: TestClient):
    response = client.get("/companies/4170/kpis", params={"years": "2023"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2023]
    assert payload["annual"] == {"columns": [], "rows": []}
    assert payload["quarterly"] == {"columns": [], "rows": []}


def test_refresh_status_returns_operational_rows(client: TestClient):
    response = client.get("/refresh-status")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["last_status"] == "success"


def test_base_health_returns_snapshot(client: TestClient):
    response = client.get("/base-health", params={"start_year": 2023, "end_year": 2024})

    assert response.status_code == 200
    payload = response.json()
    assert payload["start_year"] == 2023
    assert payload["end_year"] == 2024
    assert payload["health_status"] in {"ok", "atencao", "critico"}


def test_missing_required_table_returns_503(tmp_path: Path):
    settings = build_settings(project_root=tmp_path)
    settings.paths.canonical_accounts_path.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.canonical_accounts_path.write_text("CD_CONTA,STANDARD_NAME\n1,Ativo\n", encoding="utf-8")
    settings.paths.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.db_path.touch()

    app = create_app(settings=settings)
    with TestClient(app) as client:
        response = client.get("/companies")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_service_failure_returns_503(client: TestClient):
    app = client.app
    original_service = app.state.read_service

    class BrokenService:
        engine = original_service.engine

        def list_companies(self, **_: object):
            raise RuntimeError("database is down")

    app.state.read_service = BrokenService()
    try:
        with TestClient(app, raise_server_exceptions=False) as broken_client:
            response = broken_client.get("/companies")
    finally:
        app.state.read_service = original_service

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_companies_reject_invalid_page(client: TestClient):
    response = client.get("/companies", params={"page": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_companies_reject_invalid_page_size(client: TestClient):
    response = client.get("/companies", params={"page_size": 101})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Summary endpoint
# ---------------------------------------------------------------------------


def test_company_summary_returns_blocks(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2023,2024"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cd_cvm"] == 9512
    assert payload["years"] == [2023, 2024]
    assert len(payload["blocks"]) >= 1
    assert payload["blocks"][0]["stmt_type"] in {"DRE", "BPA", "BPP", "DFC"}


def test_company_summary_block_columns_contain_required_fields(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2023,2024"})

    assert response.status_code == 200
    for block in response.json()["blocks"]:
        cols = block["table"]["columns"]
        assert "CD_CONTA" in cols
        assert "LABEL" in cols
        assert "IS_SUBTOTAL" in cols


def test_company_summary_is_subtotal_propagation(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2023"})

    assert response.status_code == 200
    dre_block = next((b for b in response.json()["blocks"] if b["stmt_type"] == "DRE"), None)
    assert dre_block is not None
    row_3_01 = next((r for r in dre_block["table"]["rows"] if r["CD_CONTA"] == "3.01"), None)
    assert row_3_01 is not None
    assert row_3_01["IS_SUBTOTAL"] is True


def test_company_summary_empty_blocks_when_no_data(client: TestClient):
    # year 1990 has no data for PETROBRAS → blocks should be []
    response = client.get("/companies/9512/summary", params={"years": "1990"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["blocks"] == []


def test_company_summary_404_unknown_company(client: TestClient):
    response = client.get("/companies/999999/summary", params={"years": "2024"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_company_summary_422_invalid_years(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2024,foo"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_summary_422_duplicate_years(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2024,2024"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_company_summary_years_sorted_stable(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2024,2023"})

    assert response.status_code == 200
    assert response.json()["years"] == [2023, 2024]


def test_company_summary_single_year_columns(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2024"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["years"] == [2024]
    assert len(payload["blocks"]) >= 1
    first_block = payload["blocks"][0]
    assert "2024" in first_block["table"]["columns"]
    assert "2023" not in first_block["table"]["columns"]


def test_company_summary_blocks_have_non_empty_titles(client: TestClient):
    response = client.get("/companies/9512/summary", params={"years": "2023"})

    assert response.status_code == 200
    for block in response.json()["blocks"]:
        assert isinstance(block["title"], str) and len(block["title"]) > 0


# ── Regressao: /years exclui anos com apenas dados trimestrais ITR ─────────────
# A seed do banco inclui linhas ITR para PETROBRAS (REPORT_YEAR=2025,
# PERIOD_LABEL="1Q25"). Sem o filtro PERIOD_LABEL = CAST(REPORT_YEAR AS TEXT)
# o endpoint retornaria [2023, 2024, 2025] e o Comparar usaria referenceYear=2025,
# cujas colunas nao existem no KPI bundle (KPI engine so usa dados anuais).
# Isso causaria todos os valores "-" na tabela de comparacao.

def test_company_years_excludes_itr_only_years(client: TestClient):
    """Garante que /years retorna apenas anos com DFP (PERIOD_LABEL == ano)."""
    response = client.get("/companies/9512/years")

    assert response.status_code == 200
    years = response.json()
    # 2025 so tem ITR (PERIOD_LABEL="1Q25") no seed — nao deve aparecer
    assert 2025 not in years
    # anos com DFP completo devem permanecer
    assert 2023 in years
    assert 2024 in years


# ── CORS: ALLOWED_ORIGINS configuravel via env var ─────────────────────────────


def test_cors_default_allows_localhost(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Sem ALLOWED_ORIGINS, apenas http://localhost:3000 e aceito."""
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cors_test.db'}")
    settings = build_settings()
    test_app = create_app(settings=settings)
    with TestClient(test_app) as c:
        response = c.options(
            "/health",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_env_var_allows_multiple_origins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """ALLOWED_ORIGINS com varios valores separados por virgula — todos aceitos."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://app.vercel.app,https://staging.vercel.app")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cors_multi.db'}")
    settings = build_settings()
    test_app = create_app(settings=settings)
    with TestClient(test_app) as c:
        for origin in ("https://app.vercel.app", "https://staging.vercel.app"):
            resp = c.options(
                "/health",
                headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
            )
            assert resp.headers.get("access-control-allow-origin") == origin, (
                f"Origem {origin} nao foi aceita pelo CORS"
            )


# ── Sentry: inicializacao condicional via SENTRY_DSN ──────────────────────────


def test_sentry_skipped_when_dsn_is_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Sem SENTRY_DSN, o Sentry nao deve ser inicializado."""
    import sentry_sdk

    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sentry_off.db'}")
    settings = build_settings()
    create_app(settings=settings)
    assert sentry_sdk.get_client().dsn is None


def test_sentry_initialized_when_dsn_is_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Com SENTRY_DSN valido, o Sentry deve ser inicializado com o environment correto."""
    import sentry_sdk

    fake_dsn = "https://pub@o0.ingest.sentry.io/0"
    monkeypatch.setenv("SENTRY_DSN", fake_dsn)
    monkeypatch.setenv("SENTRY_ENVIRONMENT", "staging")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sentry_on.db'}")
    settings = build_settings()
    create_app(settings=settings)
    client = sentry_sdk.get_client()
    assert client.dsn == fake_dsn
    assert client.options["environment"] == "staging"
