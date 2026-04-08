from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from src.settings import AppSettings, build_settings


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


def _seed_database(settings: AppSettings) -> None:
    db_path = settings.paths.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        ("PETROBRAS", 9512, "BPA", 2023, "2023", "bpa-1", "1", "Ativo Total", "Ativo Total", 0, 1000.0),
        ("PETROBRAS", 9512, "BPA", 2023, "2023", "bpa-2", "1.01", "Ativo Circulante", "Ativo Circulante", 0, 400.0),
        ("PETROBRAS", 9512, "BPA", 2023, "2023", "bpa-3", "1.01.01", "Caixa", "Caixa", 0, 100.0),
        ("PETROBRAS", 9512, "BPP", 2023, "2023", "bpp-1", "2", "Passivo Total", "Passivo Total", 0, 700.0),
        ("PETROBRAS", 9512, "BPP", 2023, "2023", "bpp-2", "2.01", "Passivo Circulante", "Passivo Circulante", 0, 250.0),
        ("PETROBRAS", 9512, "BPP", 2023, "2023", "bpp-3", "2.02", "Passivo Nao Circulante", "Passivo Nao Circulante", 0, 300.0),
        ("PETROBRAS", 9512, "BPP", 2023, "2023", "bpp-4", "2.03", "Patrimonio Liquido", "Patrimonio Liquido", 0, 300.0),
        ("PETROBRAS", 9512, "DRE", 2023, "2023", "dre-1", "3.01", "Receita Liquida", "Receita", 0, 1000.0),
        ("PETROBRAS", 9512, "DRE", 2023, "2023", "dre-2", "3.03", "Resultado Bruto", "Res_Bruto", 0, 400.0),
        ("PETROBRAS", 9512, "DRE", 2023, "2023", "dre-3", "3.05", "EBIT", "EBIT", 0, 200.0),
        ("PETROBRAS", 9512, "DRE", 2023, "2023", "dre-4", "3.11", "Lucro Liquido", "Lucro_Liq", 0, 150.0),
        ("PETROBRAS", 9512, "DFC", 2023, "2023", "dfc-1", "6.01", "Fluxo Operacional", "FCO", 0, 220.0),
        ("PETROBRAS", 9512, "DFC", 2023, "2023", "dfc-2", "6.01.01.01", "Depreciacao e amortizacao", "D&A", 0, 20.0),
        ("PETROBRAS", 9512, "DFC", 2023, "2023", "dfc-3", "6.02", "Fluxo de Investimento", "FCI", 0, -80.0),
        ("PETROBRAS", 9512, "DFC", 2023, "2023", "dfc-4", "6.03", "Fluxo de Financiamento", "FCF", 0, -30.0),
        ("PETROBRAS", 9512, "BPA", 2024, "2024", "bpa-4", "1", "Ativo Total", "Ativo Total", 0, 1200.0),
        ("PETROBRAS", 9512, "BPA", 2024, "2024", "bpa-5", "1.01", "Ativo Circulante", "Ativo Circulante", 0, 500.0),
        ("PETROBRAS", 9512, "BPA", 2024, "2024", "bpa-6", "1.01.01", "Caixa", "Caixa", 0, 120.0),
        ("PETROBRAS", 9512, "BPP", 2024, "2024", "bpp-5", "2", "Passivo Total", "Passivo Total", 0, 820.0),
        ("PETROBRAS", 9512, "BPP", 2024, "2024", "bpp-6", "2.01", "Passivo Circulante", "Passivo Circulante", 0, 280.0),
        ("PETROBRAS", 9512, "BPP", 2024, "2024", "bpp-7", "2.02", "Passivo Nao Circulante", "Passivo Nao Circulante", 0, 340.0),
        ("PETROBRAS", 9512, "BPP", 2024, "2024", "bpp-8", "2.03", "Patrimonio Liquido", "Patrimonio Liquido", 0, 380.0),
        ("PETROBRAS", 9512, "DRE", 2024, "2024", "dre-5", "3.01", "Receita Liquida", "Receita", 0, 1100.0),
        ("PETROBRAS", 9512, "DRE", 2024, "2024", "dre-6", "3.03", "Resultado Bruto", "Res_Bruto", 0, 450.0),
        ("PETROBRAS", 9512, "DRE", 2024, "2024", "dre-7", "3.05", "EBIT", "EBIT", 0, 240.0),
        ("PETROBRAS", 9512, "DRE", 2024, "2024", "dre-8", "3.11", "Lucro Liquido", "Lucro_Liq", 0, 180.0),
        ("PETROBRAS", 9512, "DFC", 2024, "2024", "dfc-5", "6.01", "Fluxo Operacional", "FCO", 0, 250.0),
        ("PETROBRAS", 9512, "DFC", 2024, "2024", "dfc-6", "6.01.01.01", "Depreciacao e amortizacao", "D&A", 0, 25.0),
        ("PETROBRAS", 9512, "DFC", 2024, "2024", "dfc-7", "6.02", "Fluxo de Investimento", "FCI", 0, -95.0),
        ("PETROBRAS", 9512, "DFC", 2024, "2024", "dfc-8", "6.03", "Fluxo de Financiamento", "FCF", 0, -50.0),
        ("VALE", 4170, "BPA", 2024, "2024", "vale-bpa", "1", "Ativo Total", "Ativo Total", 0, 900.0),
        ("VALE", 4170, "BPP", 2024, "2024", "vale-bpp", "2", "Passivo Total", "Passivo Total", 0, 500.0),
        ("VALE", 4170, "DRE", 2024, "2024", "vale-dre", "3.01", "Receita Liquida", "Receita", 0, 800.0),
        ("VALE", 4170, "DFC", 2024, "2024", "vale-dfc", "6.01", "Fluxo Operacional", "FCO", 0, 180.0),
        ("SABESP", 11223, "BPA", 2024, "2024", "sabesp-bpa", "1", "Ativo Total", "Ativo Total", 0, 650.0),
        ("SABESP", 11223, "BPP", 2024, "2024", "sabesp-bpp", "2", "Passivo Total", "Passivo Total", 0, 320.0),
        ("SABESP", 11223, "DRE", 2024, "2024", "sabesp-dre", "3.01", "Receita Liquida", "Receita", 0, 420.0),
        ("SABESP", 11223, "DFC", 2024, "2024", "sabesp-dfc", "6.01", "Fluxo Operacional", "FCO", 0, 90.0),
    ]

    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
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
        conn.execute(
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
        conn.execute(
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
        conn.executemany(
            """
            INSERT INTO companies (
                cd_cvm, company_name, nome_comercial, cnpj,
                setor_cvm, setor_analitico, company_type, ticker_b3, is_active, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (9512, "PETROBRAS", "Petrobras", "33.000.167/0001-01", "Energia", "Energia", "comercial", "PETR4", 1, "2026-04-08T09:00:00"),
                (4170, "VALE", "Vale", "33.592.510/0001-54", "Mineracao", "Materiais Basicos", "comercial", "VALE3", 1, "2026-04-08T09:00:00"),
                (11223, "SABESP", "Sabesp", "43.776.517/0001-80", "Saneamento", None, "comercial", "SBSP3", 1, "2026-04-08T09:00:00"),
                (77889, "SEM DADOS", "Sem Dados", "00.000.000/0001-00", "Financeiro", "Financeiro", "comercial", "SEMD3", 1, "2026-04-08T09:00:00"),
            ],
        )
        conn.executemany(
            """
            INSERT INTO financial_reports (
                COMPANY_NAME, CD_CVM, STATEMENT_TYPE, REPORT_YEAR, PERIOD_LABEL,
                LINE_ID_BASE, CD_CONTA, DS_CONTA, STANDARD_NAME, QA_CONFLICT, VL_CONTA
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.execute(
            """
            INSERT INTO company_refresh_status (
                cd_cvm, company_name, source_scope, last_attempt_at, last_success_at,
                last_status, last_error, last_start_year, last_end_year,
                last_rows_inserted, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                9512,
                "PETROBRAS",
                "local",
                "2026-04-08T08:50:00",
                "2026-04-08T08:55:00",
                "success",
                None,
                2023,
                2024,
                30,
                "2026-04-08T08:55:00",
            ),
        )
        conn.commit()


@pytest.fixture
def api_settings(tmp_path: Path) -> AppSettings:
    settings = build_settings(project_root=tmp_path)
    _write_canonical_accounts(settings)
    _write_active_universe_cache(settings)
    _seed_database(settings)
    return settings


@pytest.fixture
def client(api_settings: AppSettings) -> TestClient:
    app = create_app(settings=api_settings)
    with TestClient(app) as test_client:
        yield test_client
