from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from src.settings import build_settings


def test_health_returns_ok_payload(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"] == "v2-phase1"
    assert payload["database_dialect"] == "sqlite"
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


def test_companies_filters_returns_canonical_sector_options(client: TestClient):
    response = client.get("/companies/filters")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sectors"] == [
        {"sector_name": "Energia", "sector_slug": "energia", "company_count": 1},
        {"sector_name": "Materiais Basicos", "sector_slug": "materiais-basicos", "company_count": 1},
        {"sector_name": "Saneamento", "sector_slug": "saneamento", "company_count": 1},
    ]


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
