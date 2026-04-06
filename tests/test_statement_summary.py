import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.statement_summary import build_general_summary_blocks, build_statement_summary


def _statement_df(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_dre_summary_keeps_fixed_lines_and_omits_deep_details():
    df = _statement_df([
        {"CD_CONTA": "3.01", "DS_CONTA": "Receita", "STANDARD_NAME": "", "LINE_ID_BASE": "3.01", "2024": 100.0},
        {"CD_CONTA": "3.02", "DS_CONTA": "Custos", "STANDARD_NAME": "", "LINE_ID_BASE": "3.02", "2024": -40.0},
        {"CD_CONTA": "3.03", "DS_CONTA": "Resultado Bruto", "STANDARD_NAME": "", "LINE_ID_BASE": "3.03", "2024": 60.0},
        {"CD_CONTA": "3.03.01", "DS_CONTA": "Detalhe Bruto", "STANDARD_NAME": "", "LINE_ID_BASE": "3.03.01", "2024": 30.0},
        {"CD_CONTA": "3.05", "DS_CONTA": "EBIT", "STANDARD_NAME": "", "LINE_ID_BASE": "3.05", "2024": 20.0},
        {"CD_CONTA": "3.07", "DS_CONTA": "LAIR", "STANDARD_NAME": "", "LINE_ID_BASE": "3.07", "2024": 15.0},
        {"CD_CONTA": "3.11", "DS_CONTA": "Lucro Liquido", "STANDARD_NAME": "", "LINE_ID_BASE": "3.11", "2024": 10.0},
    ])

    block = build_statement_summary("DRE", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == ["3.01", "3.02", "3.03", "3.05", "3.07", "3.11"]


def test_dre_summary_falls_back_to_unique_shallow_descendant():
    df = _statement_df([
        {"CD_CONTA": "3.01", "DS_CONTA": "Receita", "STANDARD_NAME": "", "LINE_ID_BASE": "3.01", "2024": 100.0},
        {"CD_CONTA": "3.03", "DS_CONTA": "Resultado Bruto", "STANDARD_NAME": "", "LINE_ID_BASE": "3.03", "2024": 60.0},
        {"CD_CONTA": "3.05.01", "DS_CONTA": "Resultado Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "3.05.01", "2024": 20.0},
        {"CD_CONTA": "3.07", "DS_CONTA": "LAIR", "STANDARD_NAME": "", "LINE_ID_BASE": "3.07", "2024": 15.0},
        {"CD_CONTA": "3.11", "DS_CONTA": "Lucro Liquido", "STANDARD_NAME": "", "LINE_ID_BASE": "3.11", "2024": 10.0},
    ])

    block = build_statement_summary("DRE", df)

    assert block is not None
    assert "3.05.01" in block.rows["CD_CONTA"].tolist()
    assert "3.05" not in block.rows["CD_CONTA"].tolist()


def test_summary_excludes_rows_without_cd_conta():
    df = _statement_df([
        {"CD_CONTA": None, "DS_CONTA": "Sem codigo", "STANDARD_NAME": "", "LINE_ID_BASE": "DS|1", "2024": 99.0},
        {"CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "", "LINE_ID_BASE": "1", "2024": 150.0},
        {"CD_CONTA": "1.01", "DS_CONTA": "Ativo Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.01", "2024": 70.0},
        {"CD_CONTA": "1.02", "DS_CONTA": "Ativo Nao Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.02", "2024": 80.0},
    ])

    block = build_statement_summary("BPA", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == ["1", "1.01", "1.02"]
    assert "Sem codigo" not in block.rows["LABEL"].tolist()


def test_bpa_summary_includes_direct_children_of_main_groups():
    df = _statement_df([
        {"CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "", "LINE_ID_BASE": "1", "2024": 150.0},
        {"CD_CONTA": "1.01", "DS_CONTA": "Ativo Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.01", "2024": 70.0},
        {"CD_CONTA": "1.01.01", "DS_CONTA": "Caixa", "STANDARD_NAME": "", "LINE_ID_BASE": "1.01.01", "2024": 20.0},
        {"CD_CONTA": "1.01.02", "DS_CONTA": "Aplicacoes", "STANDARD_NAME": "", "LINE_ID_BASE": "1.01.02", "2024": 15.0},
        {"CD_CONTA": "1.02", "DS_CONTA": "Ativo Nao Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.02", "2024": 80.0},
        {"CD_CONTA": "1.02.03", "DS_CONTA": "Imobilizado", "STANDARD_NAME": "", "LINE_ID_BASE": "1.02.03", "2024": 55.0},
        {"CD_CONTA": "1.02.03.01", "DS_CONTA": "Detalhe Imobilizado", "STANDARD_NAME": "", "LINE_ID_BASE": "1.02.03.01", "2024": 10.0},
    ])

    block = build_statement_summary("BPA", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == ["1", "1.01", "1.01.01", "1.01.02", "1.02", "1.02.03"]


def test_bpp_summary_includes_direct_children_of_main_groups():
    df = _statement_df([
        {"CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "", "LINE_ID_BASE": "2", "2024": 150.0},
        {"CD_CONTA": "2.01", "DS_CONTA": "Passivo Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "2.01", "2024": 60.0},
        {"CD_CONTA": "2.01.01", "DS_CONTA": "Obrigacoes", "STANDARD_NAME": "", "LINE_ID_BASE": "2.01.01", "2024": 10.0},
        {"CD_CONTA": "2.01.04", "DS_CONTA": "Emprestimos CP", "STANDARD_NAME": "", "LINE_ID_BASE": "2.01.04", "2024": 20.0},
        {"CD_CONTA": "2.02", "DS_CONTA": "Passivo Nao Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "2.02", "2024": 40.0},
        {"CD_CONTA": "2.02.01", "DS_CONTA": "Emprestimos LP", "STANDARD_NAME": "", "LINE_ID_BASE": "2.02.01", "2024": 30.0},
        {"CD_CONTA": "2.03", "DS_CONTA": "Patrimonio Liquido", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03", "2024": 50.0},
        {"CD_CONTA": "2.03.01", "DS_CONTA": "Capital Social", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03.01", "2024": 20.0},
        {"CD_CONTA": "2.03.04", "DS_CONTA": "Reservas de Lucros", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03.04", "2024": 15.0},
        {"CD_CONTA": "2.03.08", "DS_CONTA": "Outros Resultados Abrangentes", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03.08", "2024": 5.0},
        {"CD_CONTA": "2.03.08.01", "DS_CONTA": "Detalhe ORA", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03.08.01", "2024": 2.0},
    ])

    block = build_statement_summary("BPP", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == [
        "2", "2.01", "2.01.01", "2.01.04", "2.02", "2.02.01", "2.03", "2.03.01", "2.03.04", "2.03.08"
    ]


def test_dfc_summary_includes_direct_children_cash_reconciliation_and_da():
    df = _statement_df([
        {"CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01", "2024": 30.0},
        {"CD_CONTA": "6.01.01", "DS_CONTA": "Caixa Gerado nas Operacoes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01", "2024": 35.0},
        {"CD_CONTA": "6.01.01.03", "DS_CONTA": "Depreciacao e Amortizacao", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01.03", "2024": 2.0},
        {"CD_CONTA": "6.02", "DS_CONTA": "Fluxo Investimento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02", "2024": -20.0},
        {"CD_CONTA": "6.02.01", "DS_CONTA": "Aquisicao de Imobilizado", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02.01", "2024": -12.0},
        {"CD_CONTA": "6.03", "DS_CONTA": "Fluxo Financiamento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03", "2024": -5.0},
        {"CD_CONTA": "6.03.01", "DS_CONTA": "Captacao de Emprestimos", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03.01", "2024": 10.0},
        {"CD_CONTA": "6.05", "DS_CONTA": "Aumento (Reducao) de Caixa e Equivalentes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.05", "2024": 5.0},
        {"CD_CONTA": "6.05.02", "DS_CONTA": "Saldo Final de Caixa e Equivalentes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.05.02", "2024": 25.0},
    ])

    block = build_statement_summary("DFC", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == [
        "6.01", "6.01.01", "6.01.01.03", "6.02", "6.02.01", "6.03", "6.03.01", "6.05", "6.05.02"
    ]


def test_dfc_summary_groups_immaterial_children_into_outros_but_keeps_da():
    df = _statement_df([
        {"CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01", "2024": 100.0, "1Q25": 80.0},
        {"CD_CONTA": "6.01.01", "DS_CONTA": "Caixa Gerado nas Operacoes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01", "2024": 120.0, "1Q25": 90.0},
        {"CD_CONTA": "6.01.01.03", "DS_CONTA": "Depreciacao e Amortizacao", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01.03", "2024": 3.0, "1Q25": 2.0},
        {"CD_CONTA": "6.01.04", "DS_CONTA": "Variacao Monetaria", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.04", "2024": 4.0, "1Q25": 3.0},
        {"CD_CONTA": "6.01.05", "DS_CONTA": "Baixa de Imobilizado", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.05", "2024": 2.0, "1Q25": 1.0},
        {"CD_CONTA": "6.02", "DS_CONTA": "Fluxo Investimento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02", "2024": -50.0, "1Q25": -40.0},
        {"CD_CONTA": "6.02.01", "DS_CONTA": "Aquisicao de Imobilizado", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02.01", "2024": -30.0, "1Q25": -15.0},
        {"CD_CONTA": "6.02.05", "DS_CONTA": "Dividendos Recebidos", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02.05", "2024": 1.0, "1Q25": 1.0},
        {"CD_CONTA": "6.03", "DS_CONTA": "Fluxo Financiamento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03", "2024": -60.0, "1Q25": -50.0},
        {"CD_CONTA": "6.03.05", "DS_CONTA": "Dividendos Pagos", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03.05", "2024": -32.0, "1Q25": -26.0},
        {"CD_CONTA": "6.03.10", "DS_CONTA": "Recompra de Acoes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03.10", "2024": -1.0, "1Q25": 0.0},
    ])

    block = build_statement_summary("DFC", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == [
        "6.01", "6.01.01", "6.01.01.03", "6.01.OUTROS",
        "6.02", "6.02.01", "6.02.OUTROS",
        "6.03", "6.03.05", "6.03.OUTROS",
    ]
    grouped = block.rows.set_index("CD_CONTA")
    assert grouped.loc["6.01.OUTROS", "2024"] == 6.0
    assert grouped.loc["6.02.OUTROS", "1Q25"] == 1.0
    assert grouped.loc["6.03.OUTROS", "2024"] == -1.0


def test_dfc_summary_keeps_da_even_when_only_deep_and_immaterial():
    df = _statement_df([
        {"CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01", "2024": 100.0},
        {"CD_CONTA": "6.01.01", "DS_CONTA": "Caixa Gerado nas Operacoes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01", "2024": 120.0},
        {"CD_CONTA": "6.01.01.04", "DS_CONTA": "Depreciacao e Amortizacao", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.01.04", "2024": 1.5},
        {"CD_CONTA": "6.01.04", "DS_CONTA": "Variacao Monetaria", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01.04", "2024": 2.0},
        {"CD_CONTA": "6.02", "DS_CONTA": "Fluxo Investimento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02", "2024": -10.0},
        {"CD_CONTA": "6.03", "DS_CONTA": "Fluxo Financiamento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03", "2024": -5.0},
    ])

    block = build_statement_summary("DFC", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == ["6.01", "6.01.01", "6.01.01.04", "6.01.OUTROS", "6.02", "6.03"]


def test_dfc_summary_keeps_standard_variation_line_and_omits_ambiguous_extra_match():
    df = _statement_df([
        {"CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01", "2024": 30.0},
        {"CD_CONTA": "6.02", "DS_CONTA": "Fluxo Investimento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02", "2024": -20.0},
        {"CD_CONTA": "6.03", "DS_CONTA": "Fluxo Financiamento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03", "2024": -5.0},
        {"CD_CONTA": "6.05", "DS_CONTA": "Aumento (Reducao) de Caixa e Equivalentes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.05", "2024": 5.0},
        {"CD_CONTA": "6.05.01", "DS_CONTA": "Variacao Liquida de Caixa e Equivalentes de Caixa", "STANDARD_NAME": "", "LINE_ID_BASE": "6.05.01", "2024": 5.0},
        {"CD_CONTA": "6.05.02", "DS_CONTA": "Saldo Final de Caixa e Equivalentes", "STANDARD_NAME": "", "LINE_ID_BASE": "6.05.02", "2024": 25.0},
    ])

    block = build_statement_summary("DFC", df)

    assert block is not None
    assert block.rows["CD_CONTA"].tolist() == ["6.01", "6.02", "6.03", "6.05", "6.05.02"]


def test_build_general_summary_blocks_preserves_statement_order():
    statements = {
        "BPP": _statement_df([
            {"CD_CONTA": "2", "DS_CONTA": "Passivo Total", "STANDARD_NAME": "", "LINE_ID_BASE": "2", "2024": 100.0},
            {"CD_CONTA": "2.01", "DS_CONTA": "Passivo Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "2.01", "2024": 40.0},
            {"CD_CONTA": "2.02", "DS_CONTA": "Passivo Nao Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "2.02", "2024": 30.0},
            {"CD_CONTA": "2.03", "DS_CONTA": "Patrimonio Liquido", "STANDARD_NAME": "", "LINE_ID_BASE": "2.03", "2024": 30.0},
        ]),
        "DRE": _statement_df([
            {"CD_CONTA": "3.01", "DS_CONTA": "Receita", "STANDARD_NAME": "", "LINE_ID_BASE": "3.01", "2024": 100.0},
            {"CD_CONTA": "3.03", "DS_CONTA": "Resultado Bruto", "STANDARD_NAME": "", "LINE_ID_BASE": "3.03", "2024": 50.0},
            {"CD_CONTA": "3.05", "DS_CONTA": "EBIT", "STANDARD_NAME": "", "LINE_ID_BASE": "3.05", "2024": 20.0},
            {"CD_CONTA": "3.07", "DS_CONTA": "LAIR", "STANDARD_NAME": "", "LINE_ID_BASE": "3.07", "2024": 10.0},
            {"CD_CONTA": "3.11", "DS_CONTA": "Lucro", "STANDARD_NAME": "", "LINE_ID_BASE": "3.11", "2024": 8.0},
        ]),
        "DFC": _statement_df([
            {"CD_CONTA": "6.01", "DS_CONTA": "Fluxo Operacional", "STANDARD_NAME": "", "LINE_ID_BASE": "6.01", "2024": 8.0},
            {"CD_CONTA": "6.02", "DS_CONTA": "Fluxo Investimento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.02", "2024": -4.0},
            {"CD_CONTA": "6.03", "DS_CONTA": "Fluxo Financiamento", "STANDARD_NAME": "", "LINE_ID_BASE": "6.03", "2024": -3.0},
        ]),
        "BPA": _statement_df([
            {"CD_CONTA": "1", "DS_CONTA": "Ativo Total", "STANDARD_NAME": "", "LINE_ID_BASE": "1", "2024": 100.0},
            {"CD_CONTA": "1.01", "DS_CONTA": "Ativo Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.01", "2024": 50.0},
            {"CD_CONTA": "1.02", "DS_CONTA": "Ativo Nao Circulante", "STANDARD_NAME": "", "LINE_ID_BASE": "1.02", "2024": 50.0},
        ]),
    }

    blocks = build_general_summary_blocks(statements)

    assert [block.stmt_type for block in blocks] == ["DRE", "BPA", "BPP", "DFC"]
