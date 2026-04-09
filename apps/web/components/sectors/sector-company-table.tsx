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
import type { SectorCompanyMetric } from "@/lib/api";
import { formatKpiValue } from "@/lib/formatters";
import { cn } from "@/lib/utils";

import { SectorCompanyLink } from "./sector-company-link";

type SectorCompanyTableProps = {
  companies: SectorCompanyMetric[];
  sectorSlug: string;
  selectedYear: number;
};

export function SectorCompanyTable({
  companies,
  sectorSlug,
  selectedYear,
}: SectorCompanyTableProps) {
  if (companies.length === 0) {
    return (
      <SurfaceCard tone="muted" padding="hero" className="space-y-5">
        <SectionHeading
          eyebrow="Empresas do setor"
          title="Nenhuma empresa comparavel neste ano"
          titleAs="h2"
          description="O setor existe, mas o recorte anual ativo nao retornou empresas listaveis com este contrato."
          descriptionClassName="text-sm leading-7"
        />
      </SurfaceCard>
    );
  }

  return (
    <section className="space-y-4">
      <SectionHeading
        eyebrow="Empresas do setor"
        title="Ranking anual por companhia"
        titleAs="h2"
        description="A ordenacao principal usa ROE decrescente e preserva empresas com metricas faltantes no fim da lista."
        descriptionClassName="text-sm leading-7"
      />

      <SurfaceCard tone="default" padding="none" className="overflow-hidden">
        <Table>
          <TableHeader className="bg-muted/35">
            <TableRow>
              <TableHead className="px-5">Rank</TableHead>
              <TableHead>Empresa</TableHead>
              <TableHead>Ticker</TableHead>
              <TableHead>ROE</TableHead>
              <TableHead>Margem EBIT</TableHead>
              <TableHead>Margem Liquida</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {companies.map((company, index) => (
              <TableRow key={company.cd_cvm} data-testid="sector-company-row">
                <TableCell className="px-5 text-muted-foreground">
                  {index + 1}
                </TableCell>
                <TableCell className="max-w-[20rem]">
                  <SectorCompanyLink
                    href={`/empresas/${company.cd_cvm}?anos=${selectedYear}`}
                    sectorSlug={sectorSlug}
                    selectedYear={selectedYear}
                    cdCvm={company.cd_cvm}
                    companyName={company.company_name}
                    className={cn(
                      "font-medium text-foreground transition-colors hover:text-primary",
                    )}
                  >
                    {company.company_name}
                  </SectorCompanyLink>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {company.ticker_b3 ?? "-"}
                </TableCell>
                <TableCell>{formatKpiValue(company.roe, "pct")}</TableCell>
                <TableCell>{formatKpiValue(company.mg_ebit, "pct")}</TableCell>
                <TableCell>{formatKpiValue(company.mg_liq, "pct")}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </SurfaceCard>
    </section>
  );
}
