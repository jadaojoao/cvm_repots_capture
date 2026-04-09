import { NextRequest, NextResponse } from "next/server";

import { proxyBinaryDownload } from "@/lib/download-proxy";

export async function GET(request: NextRequest) {
  const ids = request.nextUrl.searchParams.get("ids")?.trim() ?? "";

  if (!ids) {
    return NextResponse.json(
      {
        error: {
          code: "invalid_request",
          message: "Selecione ao menos 2 empresas para preparar o lote Excel.",
        },
      },
      { status: 422 },
    );
  }

  return proxyBinaryDownload(`/companies/export/excel-batch?ids=${encodeURIComponent(ids)}`);
}
