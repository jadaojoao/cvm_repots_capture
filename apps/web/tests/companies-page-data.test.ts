import test from "node:test";
import assert from "node:assert/strict";

import { ApiClientError } from "../lib/api.ts";
import { loadCompaniesPageData } from "../lib/companies-page-data.ts";

test("loadCompaniesPageData keeps filters when the directory request fails", async () => {
  const result = await loadCompaniesPageData(
    {
      search: "petro",
      sector: null,
      page: 1,
      pageSize: 20,
    },
    {
      fetchDirectory: async () => {
        throw new ApiClientError("Nao foi possivel conectar a API da V2.", 503, "network_error");
      },
      fetchFilters: async () => ({
        sectors: [
          {
            sector_name: "Energia",
            sector_slug: "energia",
            company_count: 1,
          },
        ],
      }),
    },
  );

  assert.equal(result.directory, null);
  assert.equal(result.filters?.sectors.length, 1);
  assert.match(result.directoryError ?? "", /Nao foi possivel conectar a API da V2/i);
  assert.equal(result.filtersError, null);
});

test("loadCompaniesPageData keeps the directory when filters fail", async () => {
  const result = await loadCompaniesPageData(
    {
      search: "",
      sector: "energia",
      page: 2,
      pageSize: 20,
    },
    {
      fetchDirectory: async () => ({
        items: [],
        pagination: {
          page: 2,
          page_size: 20,
          total_items: 0,
          total_pages: 1,
          has_next: false,
          has_previous: true,
        },
        applied_filters: {
          search: "",
          sector: "energia",
        },
      }),
      fetchFilters: async () => {
        throw new ApiClientError("A API da V2 esta indisponivel no momento.", 503, "upstream_unavailable");
      },
    },
  );

  assert.equal(result.directory?.pagination.page, 2);
  assert.equal(result.directoryError, null);
  assert.equal(result.filters, null);
  assert.match(result.filtersError ?? "", /A API da V2 nao conseguiu concluir esta solicitacao agora/i);
});
