# -*- coding: utf-8 -*-
"""
Sessão 15 — Testes pytest para src/utils.py.
Rodar: pytest tests/test_utils.py -v
"""
import sys
from pathlib import Path
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.utils import normalize_account_name, generate_line_id_base, validate_line_ids


# ──────────────────────────────────────────────────────────────────────────────
# normalize_account_name
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalizeAccountName:
    def test_basic_lowercase(self):
        assert normalize_account_name("Ativo Total") == "ativo total"

    def test_accents_removed(self):
        assert normalize_account_name("Receita Líquida") == "receita liquida"

    def test_nbsp_replaced(self):
        assert normalize_account_name("Fluxo\xa0de\xa0Caixa") == "fluxo de caixa"

    def test_multiple_spaces_collapsed(self):
        assert normalize_account_name("ATIVO   CIRCULANTE") == "ativo circulante"

    def test_em_dash_normalized(self):
        result = normalize_account_name("Provisão para Créditos–Baixa")
        assert result == "provisao para creditos-baixa"

    def test_none_returns_empty(self):
        assert normalize_account_name(None) == ""

    def test_nan_returns_empty(self):
        assert normalize_account_name(float("nan")) == ""

    def test_empty_string(self):
        assert normalize_account_name("") == ""

    def test_leading_trailing_spaces(self):
        assert normalize_account_name("  ativo total  ") == "ativo total"

    def test_already_normalized(self):
        assert normalize_account_name("ativo total") == "ativo total"

    def test_numeric_input(self):
        # Números são convertidos para string
        result = normalize_account_name(123)
        assert result == "123"


# ──────────────────────────────────────────────────────────────────────────────
# generate_line_id_base
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerateLineIdBase:
    def _row(self, cd_conta=None, ds_conta_norm="", nivel=None, grupo_dre=None):
        data = {"CD_CONTA": cd_conta, "DS_CONTA_norm": ds_conta_norm}
        if nivel is not None:
            data["NIVEL_CONTA"] = nivel
        if grupo_dre is not None:
            data["GRUPO_DRE"] = grupo_dre
        return pd.Series(data)

    def test_cd_conta_used_when_present(self):
        row = self._row(cd_conta="1.01", ds_conta_norm="ativo circulante")
        assert generate_line_id_base(row, "BPA") == "1.01"

    def test_cd_conta_stripped(self):
        row = self._row(cd_conta="  1.01  ", ds_conta_norm="ativo circulante")
        assert generate_line_id_base(row, "BPA") == "1.01"

    def test_none_cd_conta_fallback_to_hash(self):
        row = self._row(cd_conta=None, ds_conta_norm="nota explicativa")
        result = generate_line_id_base(row, "DRE")
        assert result.startswith("DS|")
        assert len(result) == 19  # "DS|" + 16 hex chars

    def test_empty_cd_conta_fallback_to_hash(self):
        row = self._row(cd_conta="", ds_conta_norm="nota")
        result = generate_line_id_base(row, "BPA")
        assert result.startswith("DS|")

    def test_hash_is_deterministic(self):
        row = self._row(cd_conta=None, ds_conta_norm="despesa financeira")
        r1 = generate_line_id_base(row, "DRE")
        r2 = generate_line_id_base(row, "DRE")
        assert r1 == r2

    def test_different_statement_types_produce_different_hashes(self):
        row = self._row(cd_conta=None, ds_conta_norm="conta generica")
        bpa = generate_line_id_base(row, "BPA")
        bpp = generate_line_id_base(row, "BPP")
        assert bpa != bpp

    def test_nivel_conta_included_in_hash(self):
        row_com = self._row(cd_conta=None, ds_conta_norm="conta x", nivel=2)
        row_sem = self._row(cd_conta=None, ds_conta_norm="conta x")
        assert generate_line_id_base(row_com, "BPA") != generate_line_id_base(row_sem, "BPA")

    def test_grupo_dre_only_used_for_dre(self):
        row = self._row(cd_conta=None, ds_conta_norm="receita", grupo_dre="REC")
        dre = generate_line_id_base(row, "DRE")
        bpa = generate_line_id_base(row, "BPA")
        assert dre != bpa  # GRUPO_DRE incluso no DRE, ignorado no BPA


# ──────────────────────────────────────────────────────────────────────────────
# validate_line_ids
# ──────────────────────────────────────────────────────────────────────────────

class TestValidateLineIds:
    def _df(self, rows):
        return pd.DataFrame(rows, columns=["LINE_ID_BASE", "VL_CONTA", "DS_CONTA"])

    def test_valid_df_returns_count(self):
        df = self._df([
            ("1.01", 100.0, "Ativo Circ"),
            ("1.02", 200.0, "Ativo NC"),
        ])
        assert validate_line_ids(df) == 2

    def test_zero_value_without_id_ok(self):
        # validate_line_ids conta notna() — zero é notna(), então conta 2
        # a guarda de erro só dispara se VL_CONTA != 0 AND id ausente
        df = self._df([
            ("1.01", 100.0, "Ativo Circ"),
            (None,   0.0,   "Linha zero sem ID"),  # zero sem ID: OK (não dispara erro)
        ])
        assert validate_line_ids(df) == 2  # ambas notna()

    def test_missing_column_raises(self):
        df = pd.DataFrame({"VL_CONTA": [100.0]})
        with pytest.raises(ValueError, match="LINE_ID_BASE"):
            validate_line_ids(df)

    def test_value_without_id_raises(self):
        df = self._df([
            (None, 500.0, "Sem ID"),
        ])
        with pytest.raises(ValueError):
            validate_line_ids(df)
