import { Badge } from "@/components/ui/badge";
import type { HealthResponse } from "@/lib/api";
import { formatCompactInteger } from "@/lib/formatters";

type TrustStripProps = {
  health: HealthResponse | null;
  totalCompanies: number | null;
};

export function TrustStrip({ health, totalCompanies }: TrustStripProps) {
  const statusLabel = health?.status === "ok" ? "API online" : "API indisponível";
  const dialectLabel = health?.database_dialect
    ? health.database_dialect.toUpperCase()
    : "N/A";

  return (
    <div className="border-y border-border/60 bg-background/70">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-4 text-sm text-muted-foreground sm:px-6 md:flex-row md:items-center md:justify-between lg:px-10">
        <div className="flex flex-wrap items-center gap-3">
          <Badge className="rounded-full bg-primary px-3 py-1 text-[0.68rem] font-medium uppercase tracking-[0.2em] text-primary-foreground">
            Fonte CVM
          </Badge>
          <span>{statusLabel}</span>
          <span>Banco: {dialectLabel}</span>
          <span>
            {totalCompanies !== null
              ? `${formatCompactInteger(totalCompanies)} empresas com dados`
              : "Diretório público em leitura"}
          </span>
        </div>
        <p className="max-w-xl text-sm leading-6">
          Fluxo inicial focado em descoberta por empresa, leitura histórica e
          navegação rasa antes das áreas de comparação e contexto setorial.
        </p>
      </div>
    </div>
  );
}
