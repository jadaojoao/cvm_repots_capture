import Link from "next/link";
import { ChevronRightIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CompanyInfo } from "@/lib/api";

type CompanyHeaderProps = {
  company: CompanyInfo;
  selectedYears: number[];
};

export function CompanyHeader({
  company,
  selectedYears,
}: CompanyHeaderProps) {
  return (
    <div className="space-y-5">
      <nav aria-label="breadcrumb">
        <ol className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <li>
            <Link href="/" className="hover:text-foreground">
              Home
            </Link>
          </li>
          <li className="flex items-center gap-2">
            <ChevronRightIcon className="size-4" />
            <Link href="/empresas" className="hover:text-foreground">
              Empresas
            </Link>
          </li>
          <li className="flex items-center gap-2 text-foreground">
            <ChevronRightIcon className="size-4 text-muted-foreground" />
            <span>{company.company_name}</span>
          </li>
        </ol>
      </nav>

      <div className="flex flex-col gap-6 rounded-[1.75rem] border border-border/70 bg-background/90 px-6 py-6 shadow-[0_24px_70px_-45px_rgba(16,30,24,0.35)] sm:px-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="rounded-full bg-secondary px-3 py-1 text-[0.68rem] uppercase tracking-[0.18em] text-secondary-foreground">
                PG-03 · Detalhe da empresa
              </Badge>
              <Badge
                variant="outline"
                className="rounded-full border-border/80 bg-background/75 text-[0.7rem] uppercase tracking-[0.16em] text-muted-foreground"
              >
                CVM {company.cd_cvm}
              </Badge>
            </div>

            <div className="space-y-3">
              <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
                {company.company_name}
              </h1>
              <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                <span>{company.ticker_b3 ?? "Sem ticker"}</span>
                <span>{company.sector_name}</span>
                <span>{selectedYears.join(", ")}</span>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Button variant="outline" size="lg" className="rounded-full px-5" disabled>
              Ver setor em breve
            </Button>
            <Button variant="outline" size="lg" className="rounded-full px-5" disabled>
              Comparar em breve
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
