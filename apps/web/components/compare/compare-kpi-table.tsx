import Link from "next/link";

import {
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CompareKpiRow } from "@/lib/compare-utils";
import { formatKpiValue } from "@/lib/formatters";
import type { CompareCompanyOption } from "@/lib/compare-page-data";

type CompareKpiTableProps = {
  companies: CompareCompanyOption[];
  rows: CompareKpiRow[];
  referenceYear: number;
};

function formatDeltaVsBase(
  value: number | null,
  formatType: string,
): string {
  if (value === null || Number.isNaN(value)) {
    return "Sem base comparavel";
  }

  const signal = value >= 0 ? "+" : "";
  if (formatType === "pct") {
    return `${signal}${(value * 100).toFixed(1)} pp vs base`;
  }

  return `${signal}${value.toFixed(2)}x vs base`;
}

export function CompareKpiTable({
  companies,
  rows,
  referenceYear,
}: CompareKpiTableProps) {
  return (
    <section id="resultado-comparacao" className="space-y-4 scroll-mt-28">
      <SectionHeading
        eyebrow="Resultado"
        title={`Comparacao lado a lado (${referenceYear})`}
        titleAs="h2"
        description="A primeira empresa da selecao vira a base de referencia para os deltas exibidos nas demais colunas."
        descriptionClassName="text-sm leading-7"
      />

      <SurfaceCard tone="default" padding="none" className="overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/35">
            <TableRow>
              <TableHead className="sticky left-0 z-20 bg-muted/35 px-5">Indicador</TableHead>
              {companies.map((company, index) => (
                <TableHead key={company.cd_cvm} className="min-w-64">
                  <div className="space-y-1">
                    <Link
                      href={`/empresas/${company.cd_cvm}`}
                      className="font-medium text-foreground hover:underline"
                    >
                      {company.company_name}
                    </Link>
                    <p className="text-[0.65rem] uppercase tracking-[0.16em] text-muted-foreground">
                      {company.ticker_b3 ?? "sem ticker"} - CVM {company.cd_cvm}
                      {index === 0 ? " - base" : ""}
                    </p>
                  </div>
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.kpiId}>
                <TableCell className="sticky left-0 z-10 bg-background px-5">
                  <div className="space-y-1">
                    <p className="font-medium text-foreground">{row.label}</p>
                    <p className="text-[0.68rem] uppercase tracking-[0.15em] text-muted-foreground">
                      {row.kpiId}
                    </p>
                  </div>
                </TableCell>
                {row.cells.map((cell, index) => (
                  <TableCell key={`${row.kpiId}-${companies[index]?.cd_cvm ?? index}`}>
                    <div className="space-y-1">
                      <p className="font-semibold text-foreground">
                        {formatKpiValue(cell.value, cell.formatType || row.formatType)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {index === 0
                          ? "Base de referencia"
                          : formatDeltaVsBase(cell.deltaVsBase, cell.formatType || row.formatType)}
                      </p>
                    </div>
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </SurfaceCard>
    </section>
  );
}
