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
import type { KPIBundle, TabularDataRow } from "@/lib/api";
import { FEATURED_KPIS } from "@/lib/constants";
import { formatKpiDelta, formatKpiValue } from "@/lib/formatters";

type CompanyOverviewProps = {
  bundle: KPIBundle;
};

function isYearColumn(value: string): boolean {
  return /^\d{4}$/.test(value);
}

export function CompanyOverview({ bundle }: CompanyOverviewProps) {
  const annualRows = bundle.annual.rows as TabularDataRow[];
  const yearColumns = bundle.annual.columns
    .filter(isYearColumn)
    .sort((left, right) => Number(left) - Number(right));
  const lastYear = yearColumns.at(-1);
  const kpiMap = new Map(annualRows.map((row) => [String(row.KPI_ID), row]));

  return (
    <div className="space-y-8">
      <section className="space-y-5">
        <SectionHeading
          eyebrow="Visao geral"
          title="Indicadores-chave do periodo selecionado"
          titleAs="h2"
          descriptionClassName="text-base"
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {FEATURED_KPIS.map((kpi) => {
            const row = kpiMap.get(kpi.id);
            const formatType = String(row?.FORMAT_TYPE ?? kpi.formatType);
            const currentValue = row && lastYear ? Number(row[lastYear] ?? NaN) : null;
            const deltaValue =
              row?.DELTA_YOY === null || row?.DELTA_YOY === undefined
                ? null
                : Number(row.DELTA_YOY);

            return (
              <SurfaceCard key={kpi.id} tone="subtle" padding="md">
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm text-muted-foreground">{kpi.label}</p>
                    <Badge
                      variant="outline"
                      className="rounded-full border-border/80 bg-background/70 text-[0.68rem] uppercase tracking-[0.14em] text-muted-foreground"
                    >
                      {lastYear ?? "-"}
                    </Badge>
                  </div>
                  <div className="space-y-2">
                    <p className="font-heading text-3xl tracking-[-0.04em] text-foreground">
                      {formatKpiValue(currentValue, formatType)}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {formatKpiDelta(deltaValue, formatType)}
                    </p>
                  </div>
                </div>
              </SurfaceCard>
            );
          })}
        </div>
      </section>

      <section className="space-y-4">
        <SectionHeading
          eyebrow="Matriz anual de KPIs"
          title="Leitura compacta por indicador"
          titleAs="h3"
        />

        <SurfaceCard tone="default" padding="none" className="overflow-hidden">
          <Table>
            <TableHeader className="bg-muted/35">
              <TableRow>
                <TableHead className="px-5">Indicador</TableHead>
                <TableHead>Categoria</TableHead>
                {yearColumns.map((year) => (
                  <TableHead key={year}>{year}</TableHead>
                ))}
                <TableHead>Delta YoY</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {annualRows
                .filter((row) => !Boolean(row.IS_PLACEHOLDER))
                .map((row) => {
                  const formatType = String(row.FORMAT_TYPE ?? "ratio");
                  return (
                    <TableRow key={String(row.KPI_ID)}>
                      <TableCell className="px-5 font-medium text-foreground">
                        {String(row.KPI_NOME)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {String(row.CATEGORIA)}
                      </TableCell>
                      {yearColumns.map((year) => (
                        <TableCell key={year}>
                          {formatKpiValue(
                            row[year] === null || row[year] === undefined
                              ? null
                              : Number(row[year]),
                            formatType,
                          )}
                        </TableCell>
                      ))}
                      <TableCell className="text-muted-foreground">
                        {formatKpiDelta(
                          row.DELTA_YOY === null || row.DELTA_YOY === undefined
                            ? null
                            : Number(row.DELTA_YOY),
                          formatType,
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
            </TableBody>
          </Table>
        </SurfaceCard>
      </section>
    </div>
  );
}
