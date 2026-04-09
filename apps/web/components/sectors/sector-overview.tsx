import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import type { SectorDetail } from "@/lib/api";
import { formatKpiValue } from "@/lib/formatters";

type SectorOverviewProps = {
  detail: SectorDetail;
};

const OVERVIEW_METRICS = [
  { key: "roe", label: "ROE" },
  { key: "mg_ebit", label: "Margem EBIT" },
  { key: "mg_liq", label: "Margem Liquida" },
] as const;

export function SectorOverview({ detail }: SectorOverviewProps) {
  const selectedYearSnapshot =
    detail.yearly_overview.find((entry) => entry.year === detail.selected_year) ??
    detail.yearly_overview[detail.yearly_overview.length - 1] ??
    null;

  return (
    <div className="space-y-8">
      <section className="space-y-5">
        <SectionHeading
          eyebrow="Visao geral setorial"
          title="KPIs agregados do recorte selecionado"
          titleAs="h2"
          description="Os valores abaixo refletem a leitura agregada do setor no ano ativo, mantendo lacunas como `null` em vez de inventar preenchimento."
          descriptionClassName="text-sm leading-7"
        />

        <div className="grid gap-4 md:grid-cols-3">
          {OVERVIEW_METRICS.map((metric) => (
            <SurfaceCard key={metric.key} tone="subtle" padding="md">
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm text-muted-foreground">{metric.label}</p>
                  <Badge
                    variant="outline"
                    className="rounded-full border-border/75 bg-background/70 text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground"
                  >
                    {detail.selected_year}
                  </Badge>
                </div>
                <p className="font-heading text-3xl tracking-[-0.04em] text-foreground">
                  {formatKpiValue(selectedYearSnapshot?.[metric.key] ?? null, "pct")}
                </p>
              </div>
            </SurfaceCard>
          ))}
        </div>
      </section>

      <section className="space-y-4">
        <SectionHeading
          eyebrow="Serie anual"
          title="Leitura curta por ano"
          titleAs="h3"
          description="A serie abaixo ajuda a comparar o ano ativo com o historico recente do mesmo setor."
          descriptionClassName="text-sm leading-7"
        />

        <SurfaceCard tone="default" padding="none" className="overflow-hidden">
          <Table>
            <TableHeader className="bg-muted/35">
              <TableRow>
                <TableHead className="px-5">Ano</TableHead>
                <TableHead>ROE</TableHead>
                <TableHead>Margem EBIT</TableHead>
                <TableHead>Margem Liquida</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {detail.yearly_overview.map((entry) => (
                <TableRow key={entry.year}>
                  <TableCell className="px-5 font-medium text-foreground">
                    {entry.year}
                  </TableCell>
                  <TableCell>{formatKpiValue(entry.roe, "pct")}</TableCell>
                  <TableCell>{formatKpiValue(entry.mg_ebit, "pct")}</TableCell>
                  <TableCell>{formatKpiValue(entry.mg_liq, "pct")}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </SurfaceCard>
      </section>
    </div>
  );
}
