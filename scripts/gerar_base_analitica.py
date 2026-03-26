import os

import pandas as pd


def main():
    print("Iniciando construcao da Base Analitica (Opcao 1)...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    metadata_dir = os.path.join(repo_root, "data", "metadata")

    companies_file = os.path.join(metadata_dir, "companhias_abertas_cvm_766_v2.xlsx")
    matriz_file = os.path.join(metadata_dir, "matriz_kpis_setores_cvm_agressiva_v3_open_data.xlsx")

    print(f"Lendo empresas de {companies_file}")
    df_comp = pd.read_excel(companies_file)

    print(f"Lendo matrizes de {matriz_file}")
    xls = pd.ExcelFile(matriz_file)
    cvm_map = pd.read_excel(xls, "cvm_sector_mapping")
    kpis_all = pd.read_excel(xls, "kpis_all")
    api_catalog = pd.read_excel(xls, "api_open_data_catalog")

    df_comp = df_comp.rename(columns={"setor": "setor_cvm"})
    df_comp = df_comp.merge(
        cvm_map[["cvm_sector_label", "mapped_sector"]],
        left_on="setor_cvm",
        right_on="cvm_sector_label",
        how="left",
    )

    unmapped = df_comp["mapped_sector"].isna()
    if unmapped.any():
        print(f"  AVISO: {unmapped.sum()} empresas sem mapeamento setorial. Assumindo 'OUTROS'.")
        df_comp.loc[unmapped, "mapped_sector"] = "OUTROS"

    df_comp.drop(columns=["cvm_sector_label"], inplace=True, errors="ignore")

    print("Gerando Master Table (Long Format)...")
    final_rows = []

    api_catalog_slim = api_catalog[
        ["source_id", "open_data_url", "api_or_download_url", "api_available", "auth_required", "api_doc_url"]
    ]
    api_catalog_slim = api_catalog_slim.rename(columns={"source_id": "preferred_open_source_1_id"})
    kpis_enriched = kpis_all.merge(api_catalog_slim, on="preferred_open_source_1_id", how="left")

    kpis_univ_enr = kpis_enriched[kpis_enriched["scope"] == "universal"]
    kpis_sect_enr = kpis_enriched[kpis_enriched["scope"] == "sector"]

    for _, company in df_comp.iterrows():
        cd_cvm = company["cd_cvm"]
        razao = company["razao_social"]
        setor_cvm = company["setor_cvm"]
        setor_analitico = company["mapped_sector"]

        univ_df = kpis_univ_enr.copy()
        univ_df["cd_cvm"] = cd_cvm
        univ_df["razao_social"] = razao
        univ_df["setor_cvm"] = setor_cvm
        univ_df["setor_analitico"] = setor_analitico
        final_rows.append(univ_df)

        sect_df = kpis_sect_enr[kpis_sect_enr["sector"] == setor_analitico].copy()
        if not sect_df.empty:
            sect_df["cd_cvm"] = cd_cvm
            sect_df["razao_social"] = razao
            sect_df["setor_cvm"] = setor_cvm
            sect_df["setor_analitico"] = setor_analitico
            final_rows.append(sect_df)

    master_df = pd.concat(final_rows, ignore_index=True)

    print("Estruturando Dataframe final...")
    cols_order = [
        "cd_cvm",
        "razao_social",
        "setor_cvm",
        "setor_analitico",
        "kpi_id",
        "scope",
        "category",
        "kpi_name",
        "formula_text",
        "preferred_open_source_1_id",
        "open_data_url",
        "api_or_download_url",
        "api_available",
        "auth_required",
        "api_doc_url",
    ]

    for col in cols_order:
        if col not in master_df.columns:
            master_df[col] = None

    master_df = master_df[cols_order]
    master_df["VALUE_2022"] = None
    master_df["VALUE_2023"] = None
    master_df["VALUE_2024"] = None
    master_df["LAST_UPDATED"] = None
    master_df["API_STATUS"] = "PENDING_IMPLEMENTATION"

    out_dir = os.path.join(repo_root, "output", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "base_analitica_dashboard_pronta.xlsx")
    master_df.to_excel(out_file, index=False)

    print("==========================================")
    print("Sucesso! Mapeamento concluido.")
    print(f"Total Empresas Processadas: {len(df_comp)}")
    print(f"Total de Linhas no Dashboard: {len(master_df)}")
    print(f"Tabela relacional salva em: {out_file}")
    print("==========================================")


if __name__ == "__main__":
    main()
