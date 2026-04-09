import Link from "next/link";
import { ArrowUpRightIcon, Building2Icon } from "lucide-react";

import {
  InfoChip,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { buttonVariants } from "@/components/ui/button";
import type { SectorDirectoryItem } from "@/lib/api";
import { formatCompactInteger, formatKpiValue } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type SectorDirectoryListProps = {
  items: SectorDirectoryItem[];
};

const SNAPSHOT_METRICS = [
  { key: "roe", label: "ROE" },
  { key: "mg_ebit", label: "Margem EBIT" },
  { key: "mg_liq", label: "Margem Liquida" },
] as const;

export function SectorDirectoryList({ items }: SectorDirectoryListProps) {
  if (items.length === 0) {
    return (
      <SurfaceCard
        tone="muted"
        padding="hero"
        className="items-center text-center"
      >
        <p className="font-heading text-2xl text-foreground">
          Nenhum setor disponivel.
        </p>
        <p className="max-w-2xl text-sm leading-7 text-muted-foreground">
          A API nao retornou setores prontos para leitura agora. Tente novamente
          em instantes.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <SurfaceCard
          key={item.sector_slug}
          tone="default"
          padding="lg"
          className="flex h-full flex-col justify-between gap-6"
        >
          <div className="space-y-5">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <h2 className="font-heading text-2xl leading-tight text-foreground">
                    {item.sector_name}
                  </h2>
                  <InfoChip tone="muted">
                    {formatCompactInteger(item.company_count)} empresas
                  </InfoChip>
                </div>
                <p className="text-sm leading-7 text-muted-foreground">
                  Snapshot agregado do ano mais recente disponivel para o setor.
                </p>
              </div>

              <div className="flex size-11 shrink-0 items-center justify-center rounded-full border border-border/70 bg-muted/45 text-muted-foreground">
                <Building2Icon className="size-5" />
              </div>
            </div>

            <div className="grid gap-3">
              {SNAPSHOT_METRICS.map((metric) => (
                <div
                  key={metric.key}
                  className="flex items-center justify-between gap-3 rounded-[1.2rem] border border-border/55 bg-muted/35 px-4 py-3"
                >
                  <span className="text-sm text-muted-foreground">
                    {metric.label}
                  </span>
                  <span className="font-medium text-foreground">
                    {formatKpiValue(item.snapshot[metric.key], "pct")}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between gap-3 border-t border-border/55 pt-5">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
              Base {item.latest_year ?? "-"}
            </p>
            <Link
              href={`/setores/${item.sector_slug}`}
              data-testid="sector-card-link"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Abrir setor
              <ArrowUpRightIcon className="size-4" />
            </Link>
          </div>
        </SurfaceCard>
      ))}
    </section>
  );
}
