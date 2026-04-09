import type { CompanyInfo, KPIBundle, TabularDataRow } from "./api.ts";
import { FEATURED_KPIS } from "./constants.ts";

const DEFAULT_MAX_COMPANIES = 5;

type NumberLike = number | string | null | undefined;

export type CompareCompanyBundle = {
  company: CompanyInfo;
  bundle: KPIBundle;
};

export type CompareKpiCell = {
  value: number | null;
  deltaVsBase: number | null;
  formatType: string;
};

export type CompareKpiRow = {
  kpiId: string;
  label: string;
  formatType: string;
  cells: CompareKpiCell[];
};

export function hasComparableKpiValues(rows: CompareKpiRow[]): boolean {
  return rows.some((row) =>
    row.cells.some((cell) => cell.value !== null && !Number.isNaN(cell.value)),
  );
}

function coerceFiniteNumber(value: NumberLike): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return null;
  }

  return parsed;
}

function buildAnnualIndex(bundle: KPIBundle): Map<string, TabularDataRow> {
  const index = new Map<string, TabularDataRow>();

  bundle.annual.rows.forEach((row) => {
    const kpiId = String((row as TabularDataRow).KPI_ID ?? "").trim();
    if (!kpiId) {
      return;
    }
    index.set(kpiId, row as TabularDataRow);
  });

  return index;
}

export function parseCompanyIdsCsv(
  value: string | undefined,
  maxCompanies = DEFAULT_MAX_COMPANIES,
): number[] {
  if (!value) {
    return [];
  }

  const uniqueIds = Array.from(
    new Set(
      value
        .split(",")
        .map((token) => Number.parseInt(token.trim(), 10))
        .filter((id) => Number.isFinite(id) && id > 0),
    ),
  );

  return uniqueIds.slice(0, maxCompanies);
}

export function serializeCompanyIds(ids: number[]): string {
  return Array.from(new Set(ids.filter((id) => Number.isFinite(id) && id > 0))).join(",");
}

export function intersectYears(yearGroups: number[][]): number[] {
  if (yearGroups.length === 0) {
    return [];
  }

  const normalized = yearGroups
    .map((years) =>
      Array.from(
        new Set(
          years
            .map((year) => Number.parseInt(String(year), 10))
            .filter((year) => Number.isFinite(year)),
        ),
      ).sort((left, right) => left - right),
    )
    .filter((years) => years.length > 0);

  if (normalized.length === 0) {
    return [];
  }

  return normalized.slice(1).reduce((acc, years) => {
    const yearSet = new Set(years);
    return acc.filter((year) => yearSet.has(year));
  }, normalized[0]);
}

export function buildFeaturedCompareRows(
  companies: CompareCompanyBundle[],
  referenceYear: number,
): CompareKpiRow[] {
  if (companies.length === 0) {
    return [];
  }

  const annualIndices = companies.map((entry) => buildAnnualIndex(entry.bundle));

  return FEATURED_KPIS.map((kpi) => {
    const cells = annualIndices.map((index, companyIndex) => {
      const row = index.get(kpi.id);
      const formatType = String(row?.FORMAT_TYPE ?? kpi.formatType);
      const value = coerceFiniteNumber(row?.[String(referenceYear)] as NumberLike);

      let deltaVsBase: number | null = null;
      if (companyIndex > 0) {
        const baseRow = annualIndices[0].get(kpi.id);
        const baseValue = coerceFiniteNumber(baseRow?.[String(referenceYear)] as NumberLike);
        if (value !== null && baseValue !== null) {
          deltaVsBase = value - baseValue;
        }
      }

      return {
        value,
        deltaVsBase,
        formatType,
      } satisfies CompareKpiCell;
    });

    const preferredFormat = cells.find((cell) => Boolean(cell.formatType))?.formatType ?? kpi.formatType;

    return {
      kpiId: kpi.id,
      label: kpi.label,
      formatType: preferredFormat,
      cells,
    } satisfies CompareKpiRow;
  });
}
