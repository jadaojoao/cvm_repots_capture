import test from "node:test";
import assert from "node:assert/strict";

import {
  ApiClientError,
  fetchCompanies,
  fetchCompanyFilters,
  getUserFacingErrorCopy,
} from "../lib/api.ts";
import { getFilenameFromDisposition } from "../lib/download-file.ts";

type FetchMock = typeof globalThis.fetch;

function withFetchMock(mock: FetchMock) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = mock;

  return () => {
    globalThis.fetch = originalFetch;
  };
}

test("fetchCompanies wraps transport failures into a stable network error", async () => {
  const restore = withFetchMock((async () => {
    throw new TypeError("fetch failed");
  }) as FetchMock);

  try {
    await assert.rejects(
      () => fetchCompanies({ page: 1, pageSize: 20 }),
      (error: unknown) => {
        assert.ok(error instanceof ApiClientError);
        assert.equal(error.code, "network_error");
        assert.equal(error.status, 503);

        const copy = getUserFacingErrorCopy(error);
        assert.equal(copy.title, "API indisponivel");
        assert.match(copy.message, /Nao foi possivel conectar a API da V2/i);
        return true;
      },
    );
  } finally {
    restore();
  }
});

test("fetchCompanyFilters maps upstream 5xx responses to upstream_unavailable", async () => {
  const restore = withFetchMock((async () =>
    new Response(
      JSON.stringify({
        error: {
          code: "service_unavailable",
          message: "Falha operacional ao processar a requisicao.",
        },
      }),
      {
        status: 503,
        headers: {
          "content-type": "application/json",
        },
      },
    )) as FetchMock);

  try {
    await assert.rejects(
      () => fetchCompanyFilters(),
      (error: unknown) => {
        assert.ok(error instanceof ApiClientError);
        assert.equal(error.code, "upstream_unavailable");
        assert.equal(error.status, 503);
        return true;
      },
    );
  } finally {
    restore();
  }
});

test("fetchCompanies rejects invalid payload shapes as invalid_response", async () => {
  const restore = withFetchMock((async () =>
    new Response(
      JSON.stringify({
        items: [],
      }),
      {
        status: 200,
        headers: {
          "content-type": "application/json",
        },
      },
    )) as FetchMock);

  try {
    await assert.rejects(
      () => fetchCompanies({ page: 1, pageSize: 20 }),
      (error: unknown) => {
        assert.ok(error instanceof ApiClientError);
        assert.equal(error.code, "invalid_response");
        assert.equal(error.status, 200);

        const copy = getUserFacingErrorCopy(error);
        assert.equal(copy.title, "Resposta invalida da API");
        return true;
      },
    );
  } finally {
    restore();
  }
});

test("getFilenameFromDisposition keeps quoted filenames when present", () => {
  const filename = getFilenameFromDisposition(
    'attachment; filename="PETR4_20260409.xlsx"',
    "fallback.xlsx",
  );

  assert.equal(filename, "PETR4_20260409.xlsx");
});

test("getFilenameFromDisposition falls back when header is missing", () => {
  const filename = getFilenameFromDisposition(null, "fallback.xlsx");

  assert.equal(filename, "fallback.xlsx");
});
