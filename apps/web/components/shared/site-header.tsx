import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const PRIMARY_NAV = [
  { label: "Home", href: "/" },
  { label: "Empresas", href: "/empresas" },
  { label: "Comparar", href: "/comparar" },
  { label: "Setores", href: "/setores" },
  { label: "KPIs", href: null },
  { label: "Macro", href: null },
] as const;

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/88 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-10">
        <Link
          href="/"
          className="flex items-center gap-3 text-sm font-medium tracking-[0.22em] text-foreground"
        >
          <span className="flex size-9 items-center justify-center rounded-full border border-foreground/15 bg-foreground text-xs font-semibold tracking-[0.18em] text-background">
            CVM
          </span>
          <span className="hidden font-heading text-sm uppercase text-foreground/80 sm:inline">
            Analytics
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {PRIMARY_NAV.map((item) =>
            item.href ? (
              <Link
                key={item.label}
                href={item.href}
                className={cn(
                  buttonVariants({ variant: "ghost", size: "sm" }),
                  "rounded-full px-4 text-[0.84rem] text-foreground/78 hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            ) : (
              <span
                key={item.label}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-[0.84rem] text-muted-foreground/78"
              >
                {item.label}
                <span className="h-1.5 w-1.5 rounded-full bg-border/90" />
                <span className="text-[0.64rem] font-medium uppercase tracking-[0.2em] text-muted-foreground/62">
                  Em breve
                </span>
              </span>
            ),
          )}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <span className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
            Slice publico V2
          </span>
        </div>
      </div>
    </header>
  );
}
