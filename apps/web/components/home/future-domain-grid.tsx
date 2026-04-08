import { ArrowUpRightIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { HOME_QUICK_LINKS } from "@/lib/constants";

export function FutureDomainGrid() {
  return (
    <section className="grid gap-6 border-t border-border/60 pt-10 md:grid-cols-2 xl:grid-cols-4">
      {HOME_QUICK_LINKS.map((item) => (
        <article
          key={item.label}
          className="flex min-h-40 flex-col justify-between gap-5 border-b border-border/50 pb-6 md:border-b-0"
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-heading text-xl text-foreground">{item.label}</h2>
              <Badge
                variant="outline"
                className="rounded-full border-border/80 bg-background/60 text-[0.68rem] uppercase tracking-[0.16em] text-muted-foreground"
              >
                Em breve
              </Badge>
            </div>
            <p className="text-sm leading-7 text-muted-foreground">{item.description}</p>
          </div>
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
            Aguardando próximos contratos
            <ArrowUpRightIcon className="size-3.5" />
          </div>
        </article>
      ))}
    </section>
  );
}
