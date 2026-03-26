"""
src/standardizer.py — Padronização de contas CVM por CD_CONTA.

Adiciona a coluna STANDARD_NAME a DataFrames processados pelo pipeline,
mapeando cada CD_CONTA ao nome canônico do plano de contas fixas da CVM.

Uso típico (chamado internamente pelo scraper):
    from src.standardizer import AccountStandardizer
    std = AccountStandardizer('data/canonical_accounts.csv')
    df_bpa = std.enrich(df_bpa, statement_type='BPA', empresa_tipo='comercial')
"""

from __future__ import annotations

import os
import pandas as pd
from typing import Optional


class AccountStandardizer:
    """
    Enriquece DataFrames do pipeline com o nome canônico de conta CVM.

    O canonical_csv deve ter as colunas:
        CD_CONTA, STANDARD_NAME, STATEMENT_TYPE, EMPRESA_TIPO, IS_CONSOLIDADO, NIVEL
    """

    def __init__(self, canonical_csv_path: str):
        """
        Carrega o dicionário canônico de contas.

        Args:
            canonical_csv_path: Caminho para data/canonical_accounts.csv

        Raises:
            FileNotFoundError: Se o arquivo não existir
        """
        if not os.path.exists(canonical_csv_path):
            raise FileNotFoundError(
                f"Dicionário canônico não encontrado: {canonical_csv_path}\n"
                "Execute primeiro: python scripts/build_canonical_dict.py"
            )

        self._df = pd.read_csv(canonical_csv_path, encoding='utf-8-sig', dtype=str)

        # Normaliza IS_CONSOLIDADO para bool
        if 'IS_CONSOLIDADO' in self._df.columns:
            self._df['IS_CONSOLIDADO'] = self._df['IS_CONSOLIDADO'].str.lower().isin(['true', '1', 'yes'])

        print(f"  [Standardizer] Dicionario carregado: {len(self._df)} contas canonicas")

    def _get_lookup(
        self,
        statement_type: str,
        empresa_tipo: str = 'comercial',
        is_consolidated: bool = True,
    ) -> dict[str, str]:
        """
        Constrói um dicionário CD_CONTA -> STANDARD_NAME filtrado por (statement, empresa, cons.).
        Inclui fallback: se não achar con/ind, tenta o oposto; depois descarta empresa_tipo.
        """
        df = self._df

        # Filtros em ordem decrescente de especificidade
        for tipo in [empresa_tipo, 'comercial']:
            for cons in [is_consolidated, not is_consolidated]:
                subset = df[
                    (df['STATEMENT_TYPE'] == statement_type) &
                    (df['EMPRESA_TIPO'] == tipo) &
                    (df['IS_CONSOLIDADO'] == cons)
                ]
                if not subset.empty:
                    return dict(zip(subset['CD_CONTA'], subset['STANDARD_NAME']))

        # Último recurso: qualquer linha com esse statement_type
        subset = df[df['STATEMENT_TYPE'] == statement_type]
        return dict(zip(subset['CD_CONTA'], subset['STANDARD_NAME']))

    def enrich(
        self,
        df: pd.DataFrame,
        statement_type: str,
        empresa_tipo: str = 'comercial',
        is_consolidated: bool = True,
    ) -> pd.DataFrame:
        """
        Adiciona a coluna STANDARD_NAME ao DataFrame.

        LINE_ID_BASEs que começam com 'DS|' (hash sintético, sem CD_CONTA)
        recebem STANDARD_NAME = None automaticamente — são contas discricionárias
        que a empresa inventou e não fazem parte do plano fixo.

        Args:
            df: DataFrame com coluna LINE_ID_BASE (= CD_CONTA) como coluna ou índice
            statement_type: 'BPA', 'BPP', 'DRE', 'DFC', 'DMPL', 'DVA'
            empresa_tipo: 'comercial', 'financeira' ou 'seguradora'
            is_consolidated: True se demonstração consolidada

        Returns:
            DataFrame com coluna STANDARD_NAME adicionada após DS_CONTA
        """
        df = df.copy()

        # Garante que LINE_ID_BASE seja coluna (pode estar no índice)
        if 'LINE_ID_BASE' not in df.columns and df.index.name == 'LINE_ID_BASE':
            df = df.reset_index()
            had_index = True
        else:
            had_index = False

        lookup = self._get_lookup(statement_type, empresa_tipo, is_consolidated)

        def _map(lid: str) -> Optional[str]:
            if pd.isna(lid) or str(lid).startswith('DS|'):
                return None
            return lookup.get(str(lid))

        df['STANDARD_NAME'] = df['LINE_ID_BASE'].apply(_map)

        # Reposiciona STANDARD_NAME logo após DS_CONTA (se existir)
        if 'DS_CONTA' in df.columns:
            cols = list(df.columns)
            cols.remove('STANDARD_NAME')
            pos = cols.index('DS_CONTA') + 1
            cols.insert(pos, 'STANDARD_NAME')
            df = df[cols]

        if had_index:
            df = df.set_index('LINE_ID_BASE')

        return df

    def coverage_report(
        self,
        processed_reports: dict[str, pd.DataFrame],
    ) -> dict[str, dict]:
        """
        Calcula o relatório de cobertura de padronização por demonstração.

        Returns:
            dict com {statement: {total, matched, pct, unmatched_accounts}}
        """
        report = {}

        for stmt, df in processed_reports.items():
            if df is None or df.empty:
                continue

            df_reset = df.reset_index() if df.index.name == 'LINE_ID_BASE' else df

            if 'STANDARD_NAME' not in df_reset.columns:
                continue

            total = len(df_reset)
            matched = df_reset['STANDARD_NAME'].notna().sum()
            pct = round(100 * matched / total, 1) if total > 0 else 0.0

            # Contas sem STANDARD_NAME (excluindo hash DS|)
            unmatched = df_reset[
                df_reset['STANDARD_NAME'].isna() &
                ~df_reset.get('LINE_ID_BASE', df_reset.index.to_series()).astype(str).str.startswith('DS|')
            ]
            unmatched_accounts = []
            if 'LINE_ID_BASE' in df_reset.columns:
                unmatched_accounts = unmatched['LINE_ID_BASE'].tolist()

            report[stmt] = {
                'total_linhas': total,
                'mapeadas': int(matched),
                'pct_cobertura': pct,
                'nao_mapeadas_CD_CONTA': unmatched_accounts[:20],  # limita a 20
            }

        return report
