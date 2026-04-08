import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  const kpiMap = new Map(
    annualRows.map((row) => [String(row.KPI_ID), row]),
  );

  return (
    <div className="space-y-8">
      <section className="space-y-5">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
            Visão geral
          </p>
          <h2 className="font-heading text-2xl text-foreground">
            Indicadores-chave do período selecionado
          </h2>
        </div>

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
              <article
                key={kpi.id}
                className="overflow-hidden rounded-[1.4rem] border border-border/70 bg-background/90 p-5 shadow-sm shadow-black/5"
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-muted-foreground">{kpi.label}</p>
                    <Badge
                      variant="outline"
                      className="rounded-full border-border/80 bg-background/70 text-[0.68rem] uppercase tracking-[0.14em] text-muted-foreground"
                    >
                      {lastYear ?? "—"}
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
              </article>
            );
          })}
        </div>
      </section>

      <section className="space-y-4">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
            Matriz anual de KPIs
          </p>
          <h3 className="font-heading text-2xl text-foreground">
            Leitura compacta por indicador
          </h3>
        </div>

        <div className="overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/90">
          <Table>
            <TableHeader className="bg-muted/35">
              <TableRow>
                <TableHead className="px-4">Indicador</TableHead>
                <TableHead>Categoria</TableHead>
                {yearColumns.map((year) => (
                  <TableHead key={year}>{year}</TableHead>
                ))}
                <TableHead>Δ YoY</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {annualRows
                .filter((row) => !Boolean(row.IS_PLACEHOLDER))
                .map((row) => {
                  const formatType = String(row.FORMAT_TYPE ?? "ratio");
                  return (
                    <TableRow key={String(row.KPI_ID)}>
                      <TableCell className="px-4 font-medium text-foreground">
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
        </div>
      </section>
    </div>
  );
}
