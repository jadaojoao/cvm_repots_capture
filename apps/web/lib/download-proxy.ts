import { NextResponse } from "next/server";

import { buildApiUrl } from "@/lib/api";

type ApiErrorShape = {
  error?: {
    code?: string;
    message?: string;
  };
};

function pickDownloadHeaders(response: Response): Headers {
  const headers = new Headers();
  const contentType = response.headers.get("content-type");
  const contentDisposition = response.headers.get("content-disposition");

  if (contentType) {
    headers.set("content-type", contentType);
  }

  if (contentDisposition) {
    headers.set("content-disposition", contentDisposition);
  }

  headers.set("cache-control", "no-store");
  return headers;
}

export async function proxyBinaryDownload(path: string) {
  let upstream: Response;

  try {
    upstream = await fetch(buildApiUrl(path), {
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "network_error",
          message: "Nao foi possivel conectar a API da V2.",
        },
      },
      { status: 503 },
    );
  }

  if (!upstream.ok) {
    let payload: ApiErrorShape | null = null;

    try {
      payload = (await upstream.json()) as ApiErrorShape;
    } catch {
      payload = null;
    }

    return NextResponse.json(
      payload ?? {
        error: {
          code: upstream.status >= 500 ? "upstream_unavailable" : "unknown_error",
          message:
            upstream.status >= 500
              ? "A API da V2 nao conseguiu preparar o download agora."
              : "Falha ao preparar o download solicitado.",
        },
      },
      { status: upstream.status },
    );
  }

  return new NextResponse(await upstream.arrayBuffer(), {
    status: upstream.status,
    headers: pickDownloadHeaders(upstream),
  });
}
