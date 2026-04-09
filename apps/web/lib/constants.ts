export const HOME_QUICK_LINKS = [
  {
    label: "Comparar",
    description: "Comparacao lado a lado entre empresas e contextos setoriais.",
    href: "/comparar",
    status: "disponivel",
  },
  {
    label: "Setores",
    description: "Leitura tematica por clusters e cadeias produtivas.",
    href: "/setores",
    status: "disponivel",
  },
  {
    label: "KPIs",
    description: "Catalogo navegavel dos indicadores-chave da plataforma.",
    href: null,
    status: "em-breve",
  },
  {
    label: "Macro",
    description: "Contexto macroeconomico para leitura dos resultados.",
    href: null,
    status: "em-breve",
  },
] as const;

export const FEATURED_KPIS = [
  { id: "MG_BRUTA", label: "Margem Bruta", formatType: "pct" },
  { id: "MG_EBITDA", label: "Margem EBITDA", formatType: "pct" },
  { id: "MG_EBIT", label: "Margem EBIT", formatType: "pct" },
  { id: "MG_LIQ", label: "Margem Liquida", formatType: "pct" },
  { id: "ROE", label: "ROE", formatType: "pct" },
  { id: "ROA", label: "ROA", formatType: "pct" },
  { id: "FCO_REC", label: "FCO / Receita", formatType: "pct" },
  { id: "LIQ_CORR", label: "Liquidez Corrente", formatType: "ratio" },
] as const;

export const DETAIL_TABS = [
  { value: "visao-geral", label: "Visao Geral" },
  { value: "demonstracoes", label: "Demonstracoes" },
] as const;

export const STATEMENT_OPTIONS = [
  { value: "DRE", label: "DRE" },
  { value: "BPA", label: "BPA" },
  { value: "BPP", label: "BPP" },
  { value: "DFC", label: "DFC" },
] as const;

export const STATEMENT_LABELS: Record<string, string> = {
  DRE: "Demonstracao de Resultado",
  BPA: "Balanco Patrimonial Ativo",
  BPP: "Balanco Patrimonial Passivo",
  DFC: "Fluxo de Caixa",
};

const SUBTOTAL_MAP = {
  DRE: new Set(["3.01", "3.03", "3.05", "3.07", "3.11"]),
  BPA: new Set(["1", "1.01", "1.02"]),
  BPP: new Set(["2", "2.01", "2.02", "2.03"]),
  DFC: new Set(["6.01", "6.02", "6.03"]),
} as const;

export function isStatementSubtotal(
  statementType: string,
  accountCode: string | null | undefined,
): boolean {
  if (!accountCode) {
    return false;
  }

  return SUBTOTAL_MAP[statementType as keyof typeof SUBTOTAL_MAP]?.has(accountCode) ?? false;
}
