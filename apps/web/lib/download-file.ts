"use client";

import { ApiClientError } from "./api.ts";

type ApiErrorShape = {
  error?: {
    code?: string;
    message?: string;
  };
};

export function getFilenameFromDisposition(
  contentDisposition: string | null,
  fallbackFilename: string,
): string {
  if (!contentDisposition) {
    return fallbackFilename;
  }

  const utfMatch = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    try {
      return decodeURIComponent(utfMatch[1]);
    } catch {
      return utfMatch[1];
    }
  }

  const quotedMatch = contentDisposition.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const bareMatch = contentDisposition.match(/filename\s*=\s*([^;]+)/i);
  if (bareMatch?.[1]) {
    return bareMatch[1].trim();
  }

  return fallbackFilename;
}

async function toDownloadError(response: Response): Promise<ApiClientError> {
  let payload: ApiErrorShape | null = null;

  try {
    payload = (await response.json()) as ApiErrorShape;
  } catch {
    payload = null;
  }

  const code = payload?.error?.code ?? "unknown_error";
  const message = payload?.error?.message;

  if (response.status === 404) {
    return new ApiClientError(
      message ?? "O recurso solicitado nao foi encontrado.",
      response.status,
      code ?? "not_found",
    );
  }

  if (response.status === 422) {
    return new ApiClientError(
      message ?? "A requisicao enviada para download nao foi aceita.",
      response.status,
      code ?? "invalid_request",
    );
  }

  if (response.status >= 500) {
    return new ApiClientError(
      message ?? "A API da V2 nao conseguiu preparar o download agora.",
      response.status,
      code ?? "upstream_unavailable",
    );
  }

  return new ApiClientError(
    message ?? `Falha ao preparar download (${response.status}).`,
    response.status,
    code,
  );
}

export async function downloadFile(
  endpoint: string,
  fallbackFilename: string,
): Promise<string> {
  let response: Response;

  try {
    response = await fetch(endpoint, {
      method: "GET",
      cache: "no-store",
    });
  } catch {
    throw new ApiClientError(
      "Nao foi possivel conectar a API da V2.",
      503,
      "network_error",
    );
  }

  if (!response.ok) {
    throw await toDownloadError(response);
  }

  const blob = await response.blob();
  const filename = getFilenameFromDisposition(
    response.headers.get("content-disposition"),
    fallbackFilename,
  );
  const objectUrl = URL.createObjectURL(blob);

  try {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    window.setTimeout(() => {
      URL.revokeObjectURL(objectUrl);
    }, 0);
  }

  return filename;
}
