import test from "node:test";
import assert from "node:assert/strict";

import {
  buildFeaturedCompareRows,
  hasComparableKpiValues,
  intersectYears,
  parseCompanyIdsCsv,
  serializeCompanyIds,
} from "../lib/compare-utils.ts";
import type { CompanyInfo, KPIBundle } from "../lib/api.ts";

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

function buildBundle(cdCvm: number, margin: number): KPIBundle {
  return {
    cd_cvm: cdCvm,
    years: [2024],
    annual: {
      columns: ["KPI_ID", "KPI_NOME", "FORMAT_TYPE", "2024"],
      rows: [
        {
          KPI_ID: "MG_BRUTA",
          KPI_NOME: "Margem Bruta",
          FORMAT_TYPE: "pct",
          "2024": margin,
        },
      ],
    },
    quarterly: {
      columns: [],
      rows: [],
    },
  };
}

test("parseCompanyIdsCsv dedupes ids and keeps positive values", () => {
  const parsed = parseCompanyIdsCsv("9512,9512,0,-7,1179,abc,347");

  assert.deepEqual(parsed, [9512, 1179, 347]);
});

test("serializeCompanyIds normalizes duplicates while preserving valid order", () => {
  const serialized = serializeCompanyIds([9512, 1179, 9512, -4, 347]);

  assert.equal(serialized, "9512,1179,347");
});

test("intersectYears returns sorted overlap across all groups", () => {
  const years = intersectYears([
    [2021, 2022, 2023, 2024],
    [2020, 2022, 2024],
    [2022, 2024, 2025],
  ]);

  assert.deepEqual(years, [2022, 2024]);
});

test("buildFeaturedCompareRows computes delta against the first company", () => {
  const rows = buildFeaturedCompareRows(
    [
      {
        company: buildCompany(9512, "PETROBRAS", "PETR4"),
        bundle: buildBundle(9512, 0.42),
      },
      {
        company: buildCompany(1179, "VALE", "VALE3"),
        bundle: buildBundle(1179, 0.37),
      },
    ],
    2024,
  );

  const grossMargin = rows.find((row) => row.kpiId === "MG_BRUTA");

  assert.ok(grossMargin);
  assert.equal(grossMargin?.cells[0].value, 0.42);
  assert.equal(grossMargin?.cells[1].value, 0.37);
  assert.ok(grossMargin?.cells[1].deltaVsBase !== null);
  assert.ok(Math.abs((grossMargin?.cells[1].deltaVsBase ?? 0) + 0.05) < 1e-9);
  assert.equal(hasComparableKpiValues(rows), true);
});

test("hasComparableKpiValues returns false when every KPI cell is empty", () => {
  const rows = buildFeaturedCompareRows(
    [
      {
        company: buildCompany(9512, "PETROBRAS", "PETR4"),
        bundle: {
          cd_cvm: 9512,
          years: [2024],
          annual: {
            columns: ["KPI_ID", "KPI_NOME", "FORMAT_TYPE", "2024"],
            rows: [],
          },
          quarterly: {
            columns: [],
            rows: [],
          },
        },
      },
      {
        company: buildCompany(1179, "VALE", "VALE3"),
        bundle: {
          cd_cvm: 1179,
          years: [2024],
          annual: {
            columns: ["KPI_ID", "KPI_NOME", "FORMAT_TYPE", "2024"],
            rows: [],
          },
          quarterly: {
            columns: [],
            rows: [],
          },
        },
      },
    ],
    2024,
  );

  assert.equal(hasComparableKpiValues(rows), false);
});
