import Link from "next/link";
import { ChevronRightIcon } from "lucide-react";

import {
  InfoChip,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
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

      <SurfaceCard tone="default" padding="lg">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <InfoChip tone="brand">PG-03 - Detalhe da empresa</InfoChip>
              <InfoChip>CVM {company.cd_cvm}</InfoChip>
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
            <Button
              variant="outline"
              size="lg"
              className="rounded-full px-5"
              disabled
            >
              Ver setor em breve
            </Button>
            <Button
              variant="outline"
              size="lg"
              className="rounded-full px-5"
              disabled
            >
              Comparar em breve
            </Button>
          </div>
        </div>
      </SurfaceCard>
    </div>
  );
}
