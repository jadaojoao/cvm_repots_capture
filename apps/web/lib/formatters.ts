export function formatCompactInteger(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR").format(value);
}

export function formatStatementValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatKpiValue(
  value: number | null | undefined,
  formatType: string,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  if (formatType === "pct") {
    return `${(value * 100).toFixed(1)}%`;
  }

  return `${value.toFixed(2)}x`;
}

export function formatKpiDelta(
  value: number | null | undefined,
  formatType: string,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "Sem variacao comparavel";
  }

  const sign = value >= 0 ? "+" : "";
  if (formatType === "pct") {
    return `${sign}${(value * 100).toFixed(1)} pp`;
  }

  return `${sign}${value.toFixed(2)}x`;
}

export function formatYearsLabel(years: number[]): string {
  if (years.length === 0) {
    return "Sem anos disponiveis";
  }

  if (years.length <= 4) {
    return years.join(", ");
  }

  return `${years[0]} - ${years[years.length - 1]}`;
}

export function getInitials(value: string): string {
  const parts = value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);

  if (parts.length === 0) {
    return "CV";
  }

  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("");
}
