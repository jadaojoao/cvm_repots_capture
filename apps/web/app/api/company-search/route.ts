import { NextRequest, NextResponse } from "next/server";

import { fetchCompanies } from "@/lib/api";

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("q")?.trim() ?? "";

  if (query.length < 2) {
    return NextResponse.json({ items: [] });
  }

  try {
    const payload = await fetchCompanies({
      search: query,
      page: 1,
      pageSize: 6,
    });

    return NextResponse.json({
      items: payload.items,
    });
  } catch {
    return NextResponse.json(
      {
        items: [],
        error: "Não foi possível buscar sugestões.",
      },
      { status: 503 },
    );
  }
}
