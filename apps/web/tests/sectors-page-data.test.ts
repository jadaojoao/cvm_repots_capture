import test from "node:test";
import assert from "node:assert/strict";

import { ApiClientError } from "../lib/api.ts";
import {
  loadSectorDetailPageData,
  loadSectorsPageData,
} from "../lib/sectors-page-data.ts";

const sampleDirectory = {
  items: [
    {
      sector_name: "Energia",
      sector_slug: "energia",
      company_count: 12,
      latest_year: 2024,
      snapshot: {
        roe: 0.18,
        mg_ebit: 0.22,
        mg_liq: 0.14,
      },
    },
  ],
};

const latestSectorDetail = {
  sector_name: "Energia",
  sector_slug: "energia",
  company_count: 12,
  available_years: [2022, 2023, 2024],
  selected_year: 2024,
  yearly_overview: [
    { year: 2022, roe: 0.12, mg_ebit: 0.18, mg_liq: 0.09 },
    { year: 2023, roe: 0.16, mg_ebit: 0.2, mg_liq: 0.11 },
    { year: 2024, roe: 0.18, mg_ebit: 0.22, mg_liq: 0.14 },
  ],
  companies: [
    {
      cd_cvm: 9512,
      company_name: "PETROBRAS",
      ticker_b3: "PETR4",
      roe: 0.25,
      mg_ebit: 0.28,
      mg_liq: 0.17,
    },
  ],
};

const scopedSectorDetail = {
  ...latestSectorDetail,
  selected_year: 2023,
  companies: [
    {
      cd_cvm: 9512,
      company_name: "PETROBRAS",
      ticker_b3: "PETR4",
      roe: 0.21,
      mg_ebit: 0.24,
      mg_liq: 0.13,
    },
  ],
};

test("loadSectorsPageData returns a stable error when the directory fails", async () => {
  const result = await loadSectorsPageData({
    fetchDirectory: async () => {
      throw new ApiClientError("Nao foi possivel conectar a API da V2.", 503, "network_error");
    },
  });

  assert.equal(result.directory, null);
  assert.match(result.directoryError ?? "", /Nao foi possivel conectar a API da V2/i);
});

test("loadSectorDetailPageData falls back to the latest year when ano is invalid", async () => {
  const calls: Array<number | undefined> = [];

  const result = await loadSectorDetailPageData("energia", "1900", "empresas", {
    fetchDetail: async (_slug, year) => {
      calls.push(year);
      return latestSectorDetail;
    },
  });

  assert.deepEqual(calls, [undefined]);
  assert.equal(result.currentTab, "empresas");
  assert.equal(result.detail?.selected_year, 2024);
});

test("loadSectorDetailPageData refetches when ano is valid and within the available range", async () => {
  const calls: Array<number | undefined> = [];

  const result = await loadSectorDetailPageData("energia", "2023", "visao-geral", {
    fetchDetail: async (_slug, year) => {
      calls.push(year);
      return year === 2023 ? scopedSectorDetail : latestSectorDetail;
    },
  });

  assert.deepEqual(calls, [undefined, 2023]);
  assert.equal(result.currentTab, "visao-geral");
  assert.equal(result.detail?.selected_year, 2023);
});

test("loadSectorDetailPageData keeps the latest detail when the scoped request fails", async () => {
  const calls: Array<number | undefined> = [];

  const result = await loadSectorDetailPageData("energia", "2023", undefined, {
    fetchDetail: async (_slug, year) => {
      calls.push(year);
      if (year === 2023) {
        throw new ApiClientError("A API da V2 esta indisponivel no momento.", 503, "upstream_unavailable");
      }
      return latestSectorDetail;
    },
  });

  assert.deepEqual(calls, [undefined, 2023]);
  assert.equal(result.detail?.selected_year, 2024);
  assert.equal(result.detailError, null);
});
