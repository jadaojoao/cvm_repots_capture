import Link from "next/link";

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
      <div className="rounded-[1.5rem] border border-dashed border-border bg-background/70 px-6 py-14 text-center">
        <p className="font-heading text-2xl text-foreground">
          Nenhuma empresa encontrada.
        </p>
        <p className="mt-3 text-sm leading-7 text-muted-foreground">
          Ajuste o termo de busca ou remova o filtro setorial para ampliar o
          diretorio disponivel.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.75rem] border border-border/70 bg-background/90 shadow-[0_24px_70px_-45px_rgba(16,30,24,0.35)]">
      <div className="divide-y divide-border/55">
        {items.map((item) => (
          <article
            key={item.cd_cvm}
            className="grid gap-5 px-5 py-5 transition-colors hover:bg-muted/35 md:grid-cols-[minmax(0,1fr)_auto]"
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="font-heading text-xl text-foreground">
                  {item.company_name}
                </h2>
                {item.ticker_b3 ? (
                  <Badge
                    variant="outline"
                    className="rounded-full border-border/80 bg-background/75 text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground"
                  >
                    {item.ticker_b3}
                  </Badge>
                ) : null}
                <Badge
                  variant="outline"
                  className="rounded-full border-border/80 bg-secondary/35 text-[0.72rem] text-foreground"
                >
                  {item.sector_name}
                </Badge>
              </div>

              <div className="flex flex-wrap gap-5 text-sm text-muted-foreground">
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
                  "rounded-full px-5",
                )}
              >
                Ver empresa
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
