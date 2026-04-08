const DETAIL_TAB_VALUES = new Set(["visao-geral", "demonstracoes"]);
const STATEMENT_VALUES = new Set(["DRE", "BPA", "BPP", "DFC"]);

export function getFirstParam(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
}

export function coercePositiveInt(
  value: string | undefined,
  fallback = 1,
): number {
  if (!value) {
    return fallback;
  }

  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return fallback;
  }

  return parsed;
}

export function parseYearsCsv(value: string | undefined): number[] {
  if (!value) {
    return [];
  }

  return Array.from(
    new Set(
      value
        .split(",")
        .map((token) => Number.parseInt(token.trim(), 10))
        .filter((year) => Number.isFinite(year)),
    ),
  ).sort((left, right) => left - right);
}

export function normalizeSelectedYears(
  availableYears: number[],
  rawYears: string | undefined,
): number[] {
  const validYears = new Set(availableYears);
  const parsed = parseYearsCsv(rawYears).filter((year) => validYears.has(year));

  if (parsed.length > 0) {
    return parsed;
  }

  return availableYears.slice(-3);
}

export function serializeYears(years: number[]): string {
  return Array.from(new Set(years)).sort((left, right) => left - right).join(",");
}

export function coerceDetailTab(
  value: string | undefined,
): "visao-geral" | "demonstracoes" {
  if (!value || !DETAIL_TAB_VALUES.has(value)) {
    return "visao-geral";
  }

  return value as "visao-geral" | "demonstracoes";
}

export function coerceStatement(
  value: string | undefined,
): "DRE" | "BPA" | "BPP" | "DFC" {
  if (!value) {
    return "DRE";
  }

  const normalized = value.toUpperCase();
  if (!STATEMENT_VALUES.has(normalized)) {
    return "DRE";
  }

  return normalized as "DRE" | "BPA" | "BPP" | "DFC";
}

export function mergeSearchParams(
  currentSearch: string,
  updates: Record<string, string | number | null | undefined>,
): string {
  const params = new URLSearchParams(currentSearch);

  Object.entries(updates).forEach(([key, value]) => {
    if (value === undefined) {
      return;
    }

    if (value === null || value === "") {
      params.delete(key);
      return;
    }

    params.set(key, String(value));
  });

  return params.toString();
}
