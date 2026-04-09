from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.api.app.main import create_app
from src.db import build_engine
from src.settings import AppSettings, build_settings

API_TEST_DATABASE_URL_ENV = "API_TEST_DATABASE_URL"


def _write_active_universe_cache(settings: AppSettings) -> None:
    settings.paths.cache_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": "2026-04-08T09:00:00",
        "rows": [
            {"cd_cvm": 9512, "company_name": "PETROBRAS"},
            {"cd_cvm": 4170, "company_name": "VALE"},
            {"cd_cvm": 11223, "company_name": "SABESP"},
            {"cd_cvm": 77889, "company_name": "SEM DADOS"},
        ],
    }
    settings.paths.active_universe_cache_path.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )


def _write_canonical_accounts(settings: AppSettings) -> None:
    settings.paths.canonical_accounts_path.parent.mkdir(parents=True, exist_ok=True)
    settings.paths.canonical_accounts_path.write_text(
        "CD_CONTA,STANDARD_NAME,STATEMENT_TYPE\n1,Ativo Total,BPA\n",
        encoding="utf-8",
    )


def _drop_seed_tables(settings: AppSettings) -> None:
    engine = build_engine(settings)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS company_refresh_status"))
        conn.execute(text("DROP TABLE IF EXISTS financial_reports"))
        conn.execute(text("DROP TABLE IF EXISTS companies"))


def _reset_seed_database(settings: AppSettings) -> None:
    if not settings.database_url:
        if settings.paths.db_path.exists():
            settings.paths.db_path.unlink(missing_ok=True)
        return
    _drop_seed_tables(settings)


def _seed_database(settings: AppSettings) -> None:
    if not settings.database_url:
        settings.paths.db_path.parent.mkdir(parents=True, exist_ok=True)

    _reset_seed_database(settings)
    engine = build_engine(settings)

    company_rows = [
        {
            "cd_cvm": 9512,
            "company_name": "PETROBRAS",
            "nome_comercial": "Petrobras",
            "cnpj": "33.000.167/0001-01",
            "setor_cvm": "Energia",
            "setor_analitico": "Energia",
            "company_type": "comercial",
            "ticker_b3": "PETR4",
            "is_active": 1,
            "updated_at": "2026-04-08T09:00:00",
        },
        {
            "cd_cvm": 4170,
            "company_name": "VALE",
            "nome_comercial": "Vale",
            "cnpj": "33.592.510/0001-54",
            "setor_cvm": "Mineracao",
            "setor_analitico": "Materiais Basicos",
            "company_type": "comercial",
            "ticker_b3": "VALE3",
            "is_active": 1,
            "updated_at": "2026-04-08T09:00:00",
        },
        {
            "cd_cvm": 11223,
            "company_name": "SABESP",
            "nome_comercial": "Sabesp",
            "cnpj": "43.776.517/0001-80",
            "setor_cvm": "Saneamento",
            "setor_analitico": None,
            "company_type": "comercial",
            "ticker_b3": "SBSP3",
            "is_active": 1,
            "updated_at": "2026-04-08T09:00:00",
        },
        {
            "cd_cvm": 77889,
            "company_name": "SEM DADOS",
            "nome_comercial": "Sem Dados",
            "cnpj": "00.000.000/0001-00",
            "setor_cvm": "Financeiro",
            "setor_analitico": "Financeiro",
            "company_type": "comercial",
            "ticker_b3": "SEMD3",
            "is_active": 1,
            "updated_at": "2026-04-08T09:00:00",
        },
    ]
    financial_rows = [
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpa-1", "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "Ativo Total", "QA_CONFLICT": 0, "VL_CONTA": 1000.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpa-2", "CD_CONTA": "1.01", "DS_CONTA": "Ativo Circulante", "STANDARD_NAME": "Ativo Circulante", "QA_CONFLICT": 0, "VL_CONTA": 400.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpa-3", "CD_CONTA": "1.01.01", "DS_CONTA": "Caixa", "STANDARD_NAME": "Caixa", "QA_CONFLICT": 0, "VL_CONTA": 100.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpp-1", "CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "Passivo Total", "QA_CONFLICT": 0, "VL_CONTA": 700.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpp-2", "CD_CONTA": "2.01", "DS_CONTA": "Passivo Circulante", "STANDARD_NAME": "Passivo Circulante", "QA_CONFLICT": 0, "VL_CONTA": 250.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpp-3", "CD_CONTA": "2.02", "DS_CONTA": "Passivo Nao Circulante", "STANDARD_NAME": "Passivo Nao Circulante", "QA_CONFLICT": 0, "VL_CONTA": 300.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "bpp-4", "CD_CONTA": "2.03", "DS_CONTA": "Patrimonio Liquido", "STANDARD_NAME": "Patrimonio Liquido", "QA_CONFLICT": 0, "VL_CONTA": 300.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dre-1", "CD_CONTA": "3.01", "DS_CONTA": "Receita Liquida", "STANDARD_NAME": "Receita", "QA_CONFLICT": 0, "VL_CONTA": 1000.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dre-2", "CD_CONTA": "3.03", "DS_CONTA": "Resultado Bruto", "STANDARD_NAME": "Res_Bruto", "QA_CONFLICT": 0, "VL_CONTA": 400.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dre-3", "CD_CONTA": "3.05", "DS_CONTA": "EBIT", "STANDARD_NAME": "EBIT", "QA_CONFLICT": 0, "VL_CONTA": 200.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dre-4", "CD_CONTA": "3.11", "DS_CONTA": "Lucro Liquido", "STANDARD_NAME": "Lucro_Liq", "QA_CONFLICT": 0, "VL_CONTA": 150.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dfc-1", "CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "FCO", "QA_CONFLICT": 0, "VL_CONTA": 220.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dfc-2", "CD_CONTA": "6.01.01.01", "DS_CONTA": "Depreciacao e amortizacao", "STANDARD_NAME": "D&A", "QA_CONFLICT": 0, "VL_CONTA": 20.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dfc-3", "CD_CONTA": "6.02", "DS_CONTA": "Fluxo de Investimento", "STANDARD_NAME": "FCI", "QA_CONFLICT": 0, "VL_CONTA": -80.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2023, "PERIOD_LABEL": "2023", "LINE_ID_BASE": "dfc-4", "CD_CONTA": "6.03", "DS_CONTA": "Fluxo de Financiamento", "STANDARD_NAME": "FCF", "QA_CONFLICT": 0, "VL_CONTA": -30.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpa-4", "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "Ativo Total", "QA_CONFLICT": 0, "VL_CONTA": 1200.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpa-5", "CD_CONTA": "1.01", "DS_CONTA": "Ativo Circulante", "STANDARD_NAME": "Ativo Circulante", "QA_CONFLICT": 0, "VL_CONTA": 500.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpa-6", "CD_CONTA": "1.01.01", "DS_CONTA": "Caixa", "STANDARD_NAME": "Caixa", "QA_CONFLICT": 0, "VL_CONTA": 120.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpp-5", "CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "Passivo Total", "QA_CONFLICT": 0, "VL_CONTA": 820.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpp-6", "CD_CONTA": "2.01", "DS_CONTA": "Passivo Circulante", "STANDARD_NAME": "Passivo Circulante", "QA_CONFLICT": 0, "VL_CONTA": 280.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpp-7", "CD_CONTA": "2.02", "DS_CONTA": "Passivo Nao Circulante", "STANDARD_NAME": "Passivo Nao Circulante", "QA_CONFLICT": 0, "VL_CONTA": 340.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "bpp-8", "CD_CONTA": "2.03", "DS_CONTA": "Patrimonio Liquido", "STANDARD_NAME": "Patrimonio Liquido", "QA_CONFLICT": 0, "VL_CONTA": 380.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dre-5", "CD_CONTA": "3.01", "DS_CONTA": "Receita Liquida", "STANDARD_NAME": "Receita", "QA_CONFLICT": 0, "VL_CONTA": 1100.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dre-6", "CD_CONTA": "3.03", "DS_CONTA": "Resultado Bruto", "STANDARD_NAME": "Res_Bruto", "QA_CONFLICT": 0, "VL_CONTA": 450.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dre-7", "CD_CONTA": "3.05", "DS_CONTA": "EBIT", "STANDARD_NAME": "EBIT", "QA_CONFLICT": 0, "VL_CONTA": 240.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dre-8", "CD_CONTA": "3.11", "DS_CONTA": "Lucro Liquido", "STANDARD_NAME": "Lucro_Liq", "QA_CONFLICT": 0, "VL_CONTA": 180.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dfc-5", "CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "FCO", "QA_CONFLICT": 0, "VL_CONTA": 250.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dfc-6", "CD_CONTA": "6.01.01.01", "DS_CONTA": "Depreciacao e amortizacao", "STANDARD_NAME": "D&A", "QA_CONFLICT": 0, "VL_CONTA": 25.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dfc-7", "CD_CONTA": "6.02", "DS_CONTA": "Fluxo de Investimento", "STANDARD_NAME": "FCI", "QA_CONFLICT": 0, "VL_CONTA": -95.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "dfc-8", "CD_CONTA": "6.03", "DS_CONTA": "Fluxo de Financiamento", "STANDARD_NAME": "FCF", "QA_CONFLICT": 0, "VL_CONTA": -50.0},
        {"COMPANY_NAME": "VALE", "CD_CVM": 4170, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "vale-bpa", "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "Ativo Total", "QA_CONFLICT": 0, "VL_CONTA": 900.0},
        {"COMPANY_NAME": "VALE", "CD_CVM": 4170, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "vale-bpp", "CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "Passivo Total", "QA_CONFLICT": 0, "VL_CONTA": 500.0},
        {"COMPANY_NAME": "VALE", "CD_CVM": 4170, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "vale-dre", "CD_CONTA": "3.01", "DS_CONTA": "Receita Liquida", "STANDARD_NAME": "Receita", "QA_CONFLICT": 0, "VL_CONTA": 800.0},
        {"COMPANY_NAME": "VALE", "CD_CVM": 4170, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "vale-dfc", "CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "FCO", "QA_CONFLICT": 0, "VL_CONTA": 180.0},
        {"COMPANY_NAME": "SABESP", "CD_CVM": 11223, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "sabesp-bpa", "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "Ativo Total", "QA_CONFLICT": 0, "VL_CONTA": 650.0},
        {"COMPANY_NAME": "SABESP", "CD_CVM": 11223, "STATEMENT_TYPE": "BPP", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "sabesp-bpp", "CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "Passivo Total", "QA_CONFLICT": 0, "VL_CONTA": 320.0},
        {"COMPANY_NAME": "SABESP", "CD_CVM": 11223, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "sabesp-dre", "CD_CONTA": "3.01", "DS_CONTA": "Receita Liquida", "STANDARD_NAME": "Receita", "QA_CONFLICT": 0, "VL_CONTA": 420.0},
        {"COMPANY_NAME": "SABESP", "CD_CVM": 11223, "STATEMENT_TYPE": "DFC", "REPORT_YEAR": 2024, "PERIOD_LABEL": "2024", "LINE_ID_BASE": "sabesp-dfc", "CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "FCO", "QA_CONFLICT": 0, "VL_CONTA": 90.0},
        # ITR-only rows: REPORT_YEAR=2025 but PERIOD_LABEL is quarterly (nao anual).
        # Esses registros sao intencional: testam que /years exclui anos sem DFP completo.
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "BPA", "REPORT_YEAR": 2025, "PERIOD_LABEL": "1Q25", "LINE_ID_BASE": "itr-bpa-1", "CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "Ativo Total", "QA_CONFLICT": 0, "VL_CONTA": 1250.0},
        {"COMPANY_NAME": "PETROBRAS", "CD_CVM": 9512, "STATEMENT_TYPE": "DRE", "REPORT_YEAR": 2025, "PERIOD_LABEL": "1Q25", "LINE_ID_BASE": "itr-dre-1", "CD_CONTA": "3.01", "DS_CONTA": "Receita Liquida", "STANDARD_NAME": "Receita", "QA_CONFLICT": 0, "VL_CONTA": 280.0},
    ]

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE companies (
                    cd_cvm INTEGER PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    nome_comercial TEXT,
                    cnpj TEXT,
                    setor_cvm TEXT,
                    setor_analitico TEXT,
                    company_type TEXT,
                    ticker_b3 TEXT,
                    is_active INTEGER,
                    updated_at TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE financial_reports (
                    COMPANY_NAME TEXT,
                    CD_CVM INTEGER,
                    STATEMENT_TYPE TEXT,
                    REPORT_YEAR INTEGER,
                    PERIOD_LABEL TEXT,
                    LINE_ID_BASE TEXT,
                    CD_CONTA TEXT,
                    DS_CONTA TEXT,
                    STANDARD_NAME TEXT,
                    QA_CONFLICT INTEGER,
                    VL_CONTA REAL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE company_refresh_status (
                    cd_cvm INTEGER PRIMARY KEY,
                    company_name TEXT,
                    source_scope TEXT,
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
                INSERT INTO companies (
                    cd_cvm, company_name, nome_comercial, cnpj,
                    setor_cvm, setor_analitico, company_type, ticker_b3, is_active, updated_at
                ) VALUES (
                    :cd_cvm, :company_name, :nome_comercial, :cnpj,
                    :setor_cvm, :setor_analitico, :company_type, :ticker_b3, :is_active, :updated_at
                )
                """
            ),
            company_rows,
        )
        conn.execute(
            text(
                """
                INSERT INTO financial_reports (
                    COMPANY_NAME, CD_CVM, STATEMENT_TYPE, REPORT_YEAR, PERIOD_LABEL,
                    LINE_ID_BASE, CD_CONTA, DS_CONTA, STANDARD_NAME, QA_CONFLICT, VL_CONTA
                ) VALUES (
                    :COMPANY_NAME, :CD_CVM, :STATEMENT_TYPE, :REPORT_YEAR, :PERIOD_LABEL,
                    :LINE_ID_BASE, :CD_CONTA, :DS_CONTA, :STANDARD_NAME, :QA_CONFLICT, :VL_CONTA
                )
                """
            ),
            financial_rows,
        )
        conn.execute(
            text(
                """
                INSERT INTO company_refresh_status (
                    cd_cvm, company_name, source_scope, last_attempt_at, last_success_at,
                    last_status, last_error, last_start_year, last_end_year,
                    last_rows_inserted, updated_at
                ) VALUES (
                    :cd_cvm, :company_name, :source_scope, :last_attempt_at, :last_success_at,
                    :last_status, :last_error, :last_start_year, :last_end_year,
                    :last_rows_inserted, :updated_at
                )
                """
            ),
            [
                {
                    "cd_cvm": 9512,
                    "company_name": "PETROBRAS",
                    "source_scope": "local",
                    "last_attempt_at": "2026-04-08T08:50:00",
                    "last_success_at": "2026-04-08T08:55:00",
                    "last_status": "success",
                    "last_error": None,
                    "last_start_year": 2023,
                    "last_end_year": 2024,
                    "last_rows_inserted": 30,
                    "updated_at": "2026-04-08T08:55:00",
                }
            ],
        )


@pytest.fixture
def api_settings(tmp_path: Path) -> AppSettings:
    settings = build_settings(project_root=tmp_path)
    explicit_database_url = os.getenv(API_TEST_DATABASE_URL_ENV)
    if explicit_database_url:
        settings = replace(settings, database_url=explicit_database_url)

    _write_canonical_accounts(settings)
    _write_active_universe_cache(settings)
    _seed_database(settings)
    yield settings
    if settings.database_url:
        _drop_seed_tables(settings)


@pytest.fixture
def client(api_settings: AppSettings) -> TestClient:
    app = create_app(settings=api_settings)
    with TestClient(app) as test_client:
        yield test_client
