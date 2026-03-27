# -*- coding: utf-8 -*-
"""
Sessão 17 — Testes pytest para src/scraper.py.
Rodar: pytest tests/test_scraper.py -v

Estratégia:
  - Nenhuma chamada real à CVM ou ao banco de dados.
  - CVMDatabase e AccountStandardizer são mockados no fixture.
  - Funções de rede (fetch_company_list, download_and_extract) usam
    unittest.mock.patch para simular requests.get.
  - Funções puras (normalize_units, _period_sort_key, etc.) são testadas
    diretamente com DataFrames construídos in-memory.
"""
import sys
import io
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: CVMScraper com todas as dependências externas mockadas
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def scraper(tmp_path):
    """
    CVMScraper isolado:
      - CVMDatabase mockado (sem SQLite real)
      - AccountStandardizer mockado (sem CSV)
      - Diretórios criados em tmp_path (sem acesso ao projeto)
    """
    with patch('src.scraper.CVMDatabase') as mock_db_cls, \
         patch('src.scraper.AccountStandardizer') as mock_std_cls:
        mock_db_cls.return_value = MagicMock()
        mock_std_cls.return_value = MagicMock()

        from src.scraper import CVMScraper
        s = CVMScraper(
            output_dir=str(tmp_path / 'output' / 'reports'),
            data_dir=str(tmp_path / 'data'),
            report_type='consolidated',
        )
        s.db = MagicMock()
        s.standardizer = None
    return s


def _make_zip_bytes(file_entries: dict) -> bytes:
    """Helper: cria um ZIP em memória com os arquivos indicados."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        for name, content in file_entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# normalize_units
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalizeUnits:
    def test_unidade_divides_by_million(self, scraper):
        df = pd.DataFrame({'VL_CONTA': [1_000_000.0], 'ESCALA_MOEDA': ['UNIDADE']})
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].iloc[0] == pytest.approx(1.0)

    def test_mil_divides_by_thousand(self, scraper):
        df = pd.DataFrame({'VL_CONTA': [5_000.0], 'ESCALA_MOEDA': ['MIL']})
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].iloc[0] == pytest.approx(5.0)

    def test_milhao_unchanged(self, scraper):
        df = pd.DataFrame({'VL_CONTA': [42.0], 'ESCALA_MOEDA': ['MILHAO']})
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].iloc[0] == pytest.approx(42.0)

    def test_mixed_scales(self, scraper):
        df = pd.DataFrame({
            'VL_CONTA':    [1_000_000.0, 2_000.0, 3.0],
            'ESCALA_MOEDA': ['UNIDADE',   'MIL',   'MILHAO'],
        })
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].tolist() == pytest.approx([1.0, 2.0, 3.0])

    def test_missing_column_returns_unchanged(self, scraper):
        df = pd.DataFrame({'VL_CONTA': [100.0]})
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].iloc[0] == 100.0

    def test_case_insensitive_unidade(self, scraper):
        df = pd.DataFrame({'VL_CONTA': [1_000_000.0], 'ESCALA_MOEDA': ['unidade']})
        result = scraper.normalize_units(df)
        assert result['VL_CONTA'].iloc[0] == pytest.approx(1.0)


# ──────────────────────────────────────────────────────────────────────────────
# _period_sort_key
# ──────────────────────────────────────────────────────────────────────────────

class TestPeriodSortKey:
    def test_annual_year(self, scraper):
        assert scraper._period_sort_key('2021') == (2021, 5)

    def test_quarterly_order(self, scraper):
        keys = [scraper._period_sort_key(f'{q}Q21') for q in range(1, 5)]
        assert keys == [(2021, 1), (2021, 2), (2021, 3), (2021, 4)]

    def test_annual_after_q4(self, scraper):
        assert scraper._period_sort_key('2021') > scraper._period_sort_key('4Q21')

    def test_cross_year_order(self, scraper):
        assert scraper._period_sort_key('1Q22') > scraper._period_sort_key('4Q21')

    def test_unknown_format_goes_to_end(self, scraper):
        assert scraper._period_sort_key('INVALID') == (9999, 0)

    def test_none_goes_to_end(self, scraper):
        assert scraper._period_sort_key(None) == (9999, 0)

    def test_full_year_in_quarterly_format(self, scraper):
        # '1Q2024' — 4-digit year in quarterly format
        key = scraper._period_sort_key('1Q2024')
        assert key == (2024, 1)


# ──────────────────────────────────────────────────────────────────────────────
# _create_period_label
# ──────────────────────────────────────────────────────────────────────────────

class TestCreatePeriodLabel:
    def _row(self, dt_refer=None, dt_ini=None, dt_fim=None):
        return {
            'DT_REFER':     pd.Timestamp(dt_refer) if dt_refer else pd.NaT,
            'DT_INI_EXERC': pd.Timestamp(dt_ini)  if dt_ini  else pd.NaT,
            'DT_FIM_EXERC': pd.Timestamp(dt_fim)  if dt_fim  else pd.NaT,
        }

    # Balance-sheet types use DT_REFER
    def test_bpa_annual_december(self, scraper):
        row = self._row(dt_refer='2024-12-31')
        assert scraper._create_period_label(row, 'BPA') == '2024'

    def test_bpa_q1_march(self, scraper):
        row = self._row(dt_refer='2024-03-31')
        assert scraper._create_period_label(row, 'BPA') == '1Q24'

    def test_bpa_q2_june(self, scraper):
        row = self._row(dt_refer='2024-06-30')
        assert scraper._create_period_label(row, 'BPA') == '2Q24'

    def test_bpa_q3_september(self, scraper):
        row = self._row(dt_refer='2024-09-30')
        assert scraper._create_period_label(row, 'BPA') == '3Q24'

    def test_bpa_nat_returns_none(self, scraper):
        row = self._row()
        assert scraper._create_period_label(row, 'BPA') is None

    # Flow statement types use DT_INI / DT_FIM
    def test_dre_annual(self, scraper):
        row = self._row(dt_ini='2024-01-01', dt_fim='2024-12-31')
        assert scraper._create_period_label(row, 'DRE') == '2024'

    def test_dre_q1(self, scraper):
        row = self._row(dt_ini='2024-01-01', dt_fim='2024-03-31')
        assert scraper._create_period_label(row, 'DRE') == '1Q24'

    def test_dfc_q2_standalone(self, scraper):
        row = self._row(dt_ini='2024-04-01', dt_fim='2024-06-30')
        assert scraper._create_period_label(row, 'DFC') == '2Q24'

    def test_dfc_q3_standalone(self, scraper):
        row = self._row(dt_ini='2024-07-01', dt_fim='2024-09-30')
        assert scraper._create_period_label(row, 'DFC') == '3Q24'

    def test_dfc_q4_standalone(self, scraper):
        row = self._row(dt_ini='2024-10-01', dt_fim='2024-12-31')
        assert scraper._create_period_label(row, 'DFC') == '4Q24'

    def test_dre_nat_returns_none(self, scraper):
        row = self._row()
        assert scraper._create_period_label(row, 'DRE') is None


# ──────────────────────────────────────────────────────────────────────────────
# _identify_period_years
# ──────────────────────────────────────────────────────────────────────────────

class TestIdentifyPeriodYears:
    def test_annual_columns(self, scraper):
        df = pd.DataFrame(columns=['LINE_ID_BASE', '2022', '2023', '2024'])
        assert scraper._identify_period_years(df) == [2022, 2023, 2024]

    def test_quarterly_columns(self, scraper):
        df = pd.DataFrame(columns=['LINE_ID_BASE', '1Q22', '2Q22', '3Q22', '4Q22'])
        assert scraper._identify_period_years(df) == [2022]

    def test_mixed_columns(self, scraper):
        df = pd.DataFrame(columns=['LINE_ID_BASE', '1Q23', '2Q23', '2023', '1Q24'])
        assert scraper._identify_period_years(df) == [2023, 2024]

    def test_no_period_columns(self, scraper):
        df = pd.DataFrame(columns=['LINE_ID_BASE', 'CD_CONTA'])
        assert scraper._identify_period_years(df) == []

    def test_non_period_columns_ignored(self, scraper):
        df = pd.DataFrame(columns=['LINE_ID_BASE', '2024', 'METADATA'])
        assert scraper._identify_period_years(df) == [2024]


# ──────────────────────────────────────────────────────────────────────────────
# coalesce_duplicate_line_ids
# ──────────────────────────────────────────────────────────────────────────────

class TestCoalesceDuplicateLineIds:
    def _wide(self, rows):
        """Helper: constrói df_wide minimal."""
        return pd.DataFrame(rows)

    def test_no_duplicates_returns_unchanged(self, scraper):
        df = self._wide([
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo', '2024': 100.0, 'QA_CONFLICT': False},
            {'LINE_ID_BASE': 'B', 'CD_CONTA': '2', 'DS_CONTA': 'Passivo', '2024': 200.0, 'QA_CONFLICT': False},
        ])
        result, logs, errors = scraper.coalesce_duplicate_line_ids(df, 'BPA')
        assert len(result) == 2
        assert errors == []

    def test_identical_duplicates_merged(self, scraper):
        df = self._wide([
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo', '2024': 100.0, 'QA_CONFLICT': False},
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo', '2024': 100.0, 'QA_CONFLICT': False},
            {'LINE_ID_BASE': 'B', 'CD_CONTA': '2', 'DS_CONTA': 'Passivo', '2024': 200.0, 'QA_CONFLICT': False},
        ])
        result, logs, errors = scraper.coalesce_duplicate_line_ids(df, 'BPA')
        assert len(result) == 2
        assert result[result['LINE_ID_BASE'] == 'A']['2024'].iloc[0] == 100.0

    def test_conflicting_duplicates_flagged(self, scraper):
        df = self._wide([
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo', '2024': 100.0, 'QA_CONFLICT': False},
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo', '2024': 999.0, 'QA_CONFLICT': False},
        ])
        result, logs, errors = scraper.coalesce_duplicate_line_ids(df, 'BPA')
        assert len(result) == 1
        assert len(errors) == 1
        assert errors[0]['type'] == 'REAL_CONFLICT'
        assert result['QA_CONFLICT'].iloc[0] is True or result['QA_CONFLICT'].iloc[0] == True

    def test_coalesce_fills_nulls_from_second_row(self, scraper):
        df = self._wide([
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo',
             '1Q24': np.nan, '2024': 100.0, 'QA_CONFLICT': False},
            {'LINE_ID_BASE': 'A', 'CD_CONTA': '1', 'DS_CONTA': 'Ativo',
             '1Q24': 50.0,  '2024': np.nan, 'QA_CONFLICT': False},
        ])
        result, logs, errors = scraper.coalesce_duplicate_line_ids(df, 'BPA')
        assert len(result) == 1
        row = result.iloc[0]
        assert row['1Q24'] == pytest.approx(50.0)
        assert row['2024'] == pytest.approx(100.0)
        assert errors == []


# ──────────────────────────────────────────────────────────────────────────────
# _compute_standalone_quarters
# ──────────────────────────────────────────────────────────────────────────────

class TestComputeStandaloneQuarters:
    def _df(self, **period_values):
        data = {'LINE_ID_BASE': ['ACC1'], 'CD_CONTA': ['1'], 'DS_CONTA': ['Conta'], 'QA_CONFLICT': [False]}
        data.update({k: [v] for k, v in period_values.items()})
        return pd.DataFrame(data)

    def test_q1_stays_as_ytd(self, scraper):
        df = self._df(**{'1Q24': 100.0, '2Q24': 250.0, '3Q24': 420.0, '2024': 600.0})
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        df_out = result[0]
        assert df_out['1Q24'].iloc[0] == pytest.approx(100.0)

    def test_q2_is_ytd2_minus_ytd1(self, scraper):
        df = self._df(**{'1Q24': 100.0, '2Q24': 250.0, '3Q24': 420.0, '2024': 600.0})
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        df_out = result[0]
        assert df_out['2Q24'].iloc[0] == pytest.approx(150.0)  # 250 - 100

    def test_q3_is_ytd3_minus_ytd2(self, scraper):
        df = self._df(**{'1Q24': 100.0, '2Q24': 250.0, '3Q24': 420.0, '2024': 600.0})
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        df_out = result[0]
        assert df_out['3Q24'].iloc[0] == pytest.approx(170.0)  # 420 - 250

    def test_q4_is_annual_minus_ytd3(self, scraper):
        df = self._df(**{'1Q24': 100.0, '2Q24': 250.0, '3Q24': 420.0, '2024': 600.0})
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        df_out = result[0]
        assert df_out['4Q24'].iloc[0] == pytest.approx(180.0)  # 600 - 420

    def test_no_data_returns_df_unchanged(self, scraper):
        df = self._df(**{'2023': 500.0})  # ano 2024 sem colunas
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        assert len(result) == 2  # (df, errors) — nenhum dado para 2024

    def test_missing_q2_warns_on_q3(self, scraper):
        # 3Q presente mas 2Q ausente → warning
        df = self._df(**{'1Q24': 100.0, '3Q24': 420.0, '2024': 600.0})
        result = scraper._compute_standalone_quarters(df, 2024, 'DFC')
        df_out, errors = result[0], result[1]
        assert any(e['type'] == 'DFC_CONVERSION_WARNING' for e in errors)


# ──────────────────────────────────────────────────────────────────────────────
# resolve_company_codes
# ──────────────────────────────────────────────────────────────────────────────

class TestResolveCompanyCodes:
    @pytest.fixture(autouse=True)
    def _set_companies_map(self, scraper):
        scraper.companies_map = {
            'PETROBRAS': 9512,
            'VALE S.A.': 4170,
            'ITAU UNIBANCO': 19348,
        }

    def test_exact_name_match(self, scraper):
        resolved = scraper.resolve_company_codes(['PETROBRAS'])
        assert resolved['PETROBRAS'] == 9512

    def test_partial_name_match(self, scraper):
        resolved = scraper.resolve_company_codes(['VALE'])
        assert list(resolved.values())[0] == 4170

    def test_numeric_string_treated_as_code(self, scraper):
        resolved = scraper.resolve_company_codes(['9512'])
        assert list(resolved.values())[0] == 9512

    def test_unknown_name_not_in_result(self, scraper):
        resolved = scraper.resolve_company_codes(['EMPRESA_INEXISTENTE'])
        assert resolved == {}

    def test_all_keyword_returns_full_map(self, scraper):
        resolved = scraper.resolve_company_codes(['all'])
        assert len(resolved) == 3

    def test_top_keyword(self, scraper):
        resolved = scraper.resolve_company_codes(['top2'])
        assert len(resolved) == 2


# ──────────────────────────────────────────────────────────────────────────────
# fetch_company_list  (mock de requests.get)
# ──────────────────────────────────────────────────────────────────────────────

class TestFetchCompanyList:
    def _mock_csv_response(self):
        csv_content = (
            "CD_CVM;DENOM_SOCIAL;DENOM_COMERC;SETOR_ATIV\n"
            "9512;PETROBRAS S.A.;PETROBRAS;Petróleo e Gás\n"
            "4170;VALE S.A.;;Mineração\n"
        ).encode('latin-1')
        mock_resp = MagicMock()
        mock_resp.content = csv_content
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    def test_companies_map_populated(self, scraper):
        with patch('requests.get', return_value=self._mock_csv_response()):
            df = scraper.fetch_company_list()
        assert df is not None
        assert 'PETROBRAS S.A.' in scraper.companies_map
        assert scraper.companies_map['PETROBRAS S.A.'] == 9512

    def test_comerc_name_also_indexed(self, scraper):
        with patch('requests.get', return_value=self._mock_csv_response()):
            scraper.fetch_company_list()
        assert 'PETROBRAS' in scraper.companies_map

    def test_setores_map_populated(self, scraper):
        with patch('requests.get', return_value=self._mock_csv_response()):
            scraper.fetch_company_list()
        assert scraper.setores_map.get('9512') == 'Petróleo e Gás'

    def test_request_error_returns_none(self, scraper):
        import requests
        with patch('requests.get', side_effect=requests.RequestException("timeout")):
            result = scraper.fetch_company_list()
        assert result is None

    def test_returns_dataframe(self, scraper):
        with patch('requests.get', return_value=self._mock_csv_response()):
            df = scraper.fetch_company_list()
        assert isinstance(df, pd.DataFrame)


# ──────────────────────────────────────────────────────────────────────────────
# download_and_extract  (mock de requests.get + zipfile)
# ──────────────────────────────────────────────────────────────────────────────

class TestDownloadAndExtract:
    def _mock_zip_response(self, scraper_suffix='con'):
        zip_bytes = _make_zip_bytes({
            f'dfp_cia_aberta_BPA_{scraper_suffix}_2024.csv': 'CD_CVM;VL_CONTA\n9512;100\n',
            f'dfp_cia_aberta_DRE_{scraper_suffix}_2024.csv': 'CD_CVM;VL_CONTA\n9512;200\n',
            'some_other_file.csv': 'irrelevant',
        })
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content = lambda chunk_size: iter([zip_bytes])
        return mock_resp

    def test_successful_download_returns_true(self, scraper):
        with patch('requests.get', return_value=self._mock_zip_response()):
            result = scraper.download_and_extract(2024, 'DFP')
        assert result is True

    def test_404_returns_false(self, scraper):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch('requests.get', return_value=mock_resp):
            result = scraper.download_and_extract(2099, 'DFP')
        assert result is False

    def test_target_files_extracted(self, scraper, tmp_path):
        with patch('requests.get', return_value=self._mock_zip_response()):
            scraper.download_and_extract(2024, 'DFP')
        extracted = list(Path(scraper.processed_dir).glob('*.csv'))
        names = [f.name for f in extracted]
        assert any('BPA_con' in n for n in names)
        assert any('DRE_con' in n for n in names)
        # Arquivo não-alvo NÃO deve ser extraído
        assert not any('other_file' in n for n in names)

    def test_request_exception_returns_false(self, scraper):
        import requests
        with patch('requests.get', side_effect=requests.RequestException("network error")):
            result = scraper.download_and_extract(2024, 'DFP')
        assert result is False

    def test_existing_zip_skips_download(self, scraper):
        # Cria um ZIP falso no raw_dir
        zip_path = Path(scraper.raw_dir) / 'dfp_cia_aberta_2024.zip'
        zip_path.write_bytes(_make_zip_bytes({
            'dfp_cia_aberta_BPA_con_2024.csv': 'CD_CVM;VL_CONTA\n',
        }))
        with patch('requests.get') as mock_get:
            scraper.download_and_extract(2024, 'DFP')
        mock_get.assert_not_called()
