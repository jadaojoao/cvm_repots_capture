import test from "node:test";
import assert from "node:assert/strict";

import { ApiClientError, type CompanyInfo, type KPIBundle } from "../lib/api.ts";
import { loadComparePageData } from "../lib/compare-page-data.ts";

function buildCompany(
  cdCvm: number,
  name: string,
  ticker: string,
): CompanyInfo {
  return {
    cd_cvm: cdCvm,
    company_name: name,
    nome_comercial: name,
    cnpj: null,
    setor_cvm: "Energia",
    setor_analitico: "Energia",
    sector_name: "Energia",
    sector_slug: "energia",
    company_type: "comercial",
    ticker_b3: ticker,
  };
}

function buildBundle(
  cdCvm: number,
  years: number[],
  margin?: number,
): KPIBundle {
  const annualRow =
    margin === undefined
      ? []
      : [
          years.reduce<Record<string, string | number>>(
            (acc, year, index) => {
              acc[String(year)] = margin - index * 0.01;
              return acc;
            },
            {
              KPI_ID: "MG_BRUTA",
              KPI_NOME: "Margem Bruta",
              FORMAT_TYPE: "pct",
            },
          ),
        ];

  return {
    cd_cvm: cdCvm,
    years,
    annual: {
      columns: ["KPI_ID", "KPI_NOME", "FORMAT_TYPE", ...years.map(String)],
      rows: annualRow,
    },
    quarterly: {
      columns: [],
      rows: [],
    },
  };
}

test("loadComparePageData reports explicit no-common-years state", async () => {
  const companies = new Map([
    [9512, buildCompany(9512, "PETROBRAS", "PETR4")],
    [1179, buildCompany(1179, "VALE", "VALE3")],
  ]);

  const result = await loadComparePageData("9512,1179", undefined, {
    fetchCompanyInfo: async (cdCvm) => companies.get(cdCvm) ?? null,
    fetchCompanyYears: async (cdCvm) =>
      cdCvm === 9512 ? [2023, 2024] : [2021, 2022],
    fetchCompanyKpis: async (cdCvm, years) => buildBundle(cdCvm, years, 0.4),
  });

  assert.equal(result.selectedCompanies.length, 2);
  assert.deepEqual(result.availableYears, []);
  assert.match(result.dataError ?? "", /anos em comum/i);
});

test("loadComparePageData keeps a partial comparison when one company fails on years", async () => {
  const companies = new Map([
    [9512, buildCompany(9512, "PETROBRAS", "PETR4")],
    [1179, buildCompany(1179, "VALE", "VALE3")],
    [347, buildCompany(347, "WEG", "WEGE3")],
  ]);

  const result = await loadComparePageData("9512,1179,347", undefined, {
    fetchCompanyInfo: async (cdCvm) => companies.get(cdCvm) ?? null,
    fetchCompanyYears: async (cdCvm) => {
      if (cdCvm === 347) {
        throw new ApiClientError("Nao foi possivel conectar a API da V2.", 503, "network_error");
      }
      return [2023, 2024];
    },
    fetchCompanyKpis: async (cdCvm, years) =>
      buildBundle(cdCvm, years, cdCvm === 9512 ? 0.42 : 0.37),
  });

  assert.equal(result.selectedCompanies.length, 3);
  assert.equal(result.comparedCompanies.length, 2);
  assert.equal(result.dataError, null);
  assert.match(result.partialErrors.join(" "), /WEG/i);
  assert.deepEqual(result.selectedYears, [2023, 2024]);
});

test("loadComparePageData normalizes raw years against the common period", async () => {
  const companies = new Map([
    [9512, buildCompany(9512, "PETROBRAS", "PETR4")],
    [1179, buildCompany(1179, "VALE", "VALE3")],
  ]);

  const result = await loadComparePageData("9512,1179", "2024,2024,1999", {
    fetchCompanyInfo: async (cdCvm) => companies.get(cdCvm) ?? null,
    fetchCompanyYears: async () => [2022, 2024, 2025],
    fetchCompanyKpis: async (cdCvm, years) =>
      buildBundle(cdCvm, years, cdCvm === 9512 ? 0.42 : 0.37),
  });

  assert.deepEqual(result.availableYears, [2022, 2024, 2025]);
  assert.deepEqual(result.selectedYears, [2024]);
  assert.equal(result.referenceYear, 2024);
});

test("loadComparePageData returns an explicit state when KPI values are empty", async () => {
  const companies = new Map([
    [9512, buildCompany(9512, "PETROBRAS", "PETR4")],
    [1179, buildCompany(1179, "VALE", "VALE3")],
  ]);

  const result = await loadComparePageData("9512,1179", "2024", {
    fetchCompanyInfo: async (cdCvm) => companies.get(cdCvm) ?? null,
    fetchCompanyYears: async () => [2024],
    fetchCompanyKpis: async (cdCvm, years) => buildBundle(cdCvm, years),
  });

  assert.equal(result.comparedCompanies.length, 2);
  assert.equal(result.rows.length, 0);
  assert.match(result.dataError ?? "", /valores comparaveis/i);
});
