import Link from "next/link";

import { SurfaceCard } from "@/components/shared/design-system-recipes";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import type { CompanyDirectoryItem } from "@/lib/api";
import { formatYearsLabel } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type CompanyDirectoryListProps = {
  items: CompanyDirectoryItem[];
};

export function CompanyDirectoryList({ items }: CompanyDirectoryListProps) {
  if (items.length === 0) {
    return (
      <SurfaceCard
        tone="muted"
        padding="hero"
        className="items-center text-center"
      >
        <p className="font-heading text-2xl text-foreground">
          Nenhuma empresa encontrada.
        </p>
        <p className="max-w-2xl text-sm leading-7 text-muted-foreground">
          Ajuste o termo de busca ou remova o filtro setorial para ampliar o
          diretorio disponivel.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard tone="default" padding="none" className="overflow-hidden">
      <div className="divide-y divide-border/55">
        {items.map((item) => (
          <article
            key={item.cd_cvm}
            className="group grid gap-6 px-6 py-6 transition-colors hover:bg-muted/35 md:grid-cols-[minmax(0,1fr)_auto]"
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="font-heading text-[1.35rem] leading-tight text-foreground">
                  {item.company_name}
                </h2>
                {item.ticker_b3 ? (
                  <Badge
                    variant="outline"
                    className="rounded-full border-border/75 bg-background/70 text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground"
                  >
                    {item.ticker_b3}
                  </Badge>
                ) : null}
                <Badge
                  variant="outline"
                  className="rounded-full border-border/75 bg-secondary/35 text-[0.72rem] text-foreground"
                >
                  {item.sector_name}
                </Badge>
              </div>

              <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted-foreground">
                <span>CVM {item.cd_cvm}</span>
                <span>{formatYearsLabel(item.anos_disponiveis)}</span>
                <span>{item.total_rows.toLocaleString("pt-BR")} linhas</span>
              </div>
            </div>

            <div className="flex items-center md:justify-end">
              <Link
                href={`/empresas/${item.cd_cvm}`}
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "rounded-full px-5 transition-transform group-hover:-translate-y-px",
                )}
              >
                Ver empresa
              </Link>
            </div>
          </article>
        ))}
      </div>
    </SurfaceCard>
  );
}
