import Link from "next/link";
import { ArrowUpRightIcon } from "lucide-react";

import {
  InfoChip,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { HOME_QUICK_LINKS } from "@/lib/constants";

export function FutureDomainGrid() {
  return (
    <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {HOME_QUICK_LINKS.map((item) => (
        <SurfaceCard
          key={item.label}
          tone="subtle"
          padding="lg"
          className="flex min-h-48 flex-col justify-between gap-6"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-3">
              <h2 className="font-heading text-xl text-foreground">{item.label}</h2>
              <InfoChip tone={item.status === "disponivel" ? "brand" : "muted"}>
                {item.status === "disponivel" ? "Disponivel" : "Em breve"}
              </InfoChip>
            </div>
            <p className="text-sm leading-7 text-muted-foreground">
              {item.description}
            </p>
          </div>
          {item.href ? (
            <Link
              href={item.href}
              className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-foreground transition-colors hover:text-primary"
            >
              Abrir superficie
              <ArrowUpRightIcon className="size-3.5" />
            </Link>
          ) : (
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
              Aguardando proximos contratos
              <ArrowUpRightIcon className="size-3.5" />
            </div>
          )}
        </SurfaceCard>
      ))}
    </section>
  );
}
