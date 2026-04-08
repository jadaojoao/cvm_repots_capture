import { InfoChip } from "@/components/shared/design-system-recipes";
import type { HealthResponse } from "@/lib/api";
import { formatCompactInteger } from "@/lib/formatters";

type TrustStripProps = {
  health: HealthResponse | null;
  totalCompanies: number | null;
};

export function TrustStrip({ health, totalCompanies }: TrustStripProps) {
  const statusLabel = health?.status === "ok" ? "API online" : "API indisponivel";
  const dialectLabel = health?.database_dialect
    ? health.database_dialect.toUpperCase()
    : "N/A";

  return (
    <div className="border-y border-border/60 bg-background/72 backdrop-blur-sm">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-4 py-4 text-sm text-muted-foreground sm:px-6 lg:px-10 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-wrap items-center gap-2.5">
          <InfoChip tone="brand">Fonte CVM</InfoChip>
          <InfoChip>{statusLabel}</InfoChip>
          <InfoChip>Banco {dialectLabel}</InfoChip>
          <InfoChip>
            {totalCompanies !== null
              ? `${formatCompactInteger(totalCompanies)} empresas com dados`
              : "Diretorio publico em leitura"}
          </InfoChip>
        </div>
        <p className="max-w-2xl text-sm leading-7">
          Fluxo inicial focado em descoberta por empresa, leitura historica e
          navegacao rasa antes das areas de comparacao e contexto setorial.
        </p>
      </div>
    </div>
  );
}
