import Link from "next/link";

const SITEMAP = [
  {
    heading: "Plataforma",
    links: [
      { label: "Home", href: "/" },
      { label: "Empresas", href: "/empresas" },
      { label: "Comparar", href: null },
      { label: "Setores", href: null },
    ],
  },
  {
    heading: "Análise",
    links: [
      { label: "KPIs", href: null },
      { label: "Macro", href: null },
      { label: "Screener", href: null },
    ],
  },
  {
    heading: "Recursos",
    links: [
      { label: "Metodologia", href: null },
      { label: "Glossário", href: null },
      { label: "Fontes", href: null },
      { label: "Design System", href: "/design-system" },
    ],
  },
  {
    heading: "Legal",
    links: [
      { label: "Privacidade", href: null },
      { label: "Termos", href: null },
    ],
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background/80">
      <div className="mx-auto w-full max-w-7xl px-4 py-12 sm:px-6 lg:px-10">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-[1fr_auto]">
          {/* Brand */}
          <div className="max-w-sm">
            <p className="font-heading text-lg text-foreground">
              Leitura pública, rápida e rastreável dos dados financeiros da CVM.
            </p>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              V2 web como camada read-only sobre a API estabilizada. Fluxos de
              refresh, comparação e domínios setoriais entram nas próximas fases.
            </p>
          </div>

          {/* Sitemap */}
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            {SITEMAP.map((section) => (
              <div key={section.heading} className="flex flex-col gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-foreground">
                  {section.heading}
                </p>
                <ul className="flex flex-col gap-2">
                  {section.links.map((link) =>
                    link.href ? (
                      <li key={link.label}>
                        <Link
                          href={link.href}
                          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                        >
                          {link.label}
                        </Link>
                      </li>
                    ) : (
                      <li key={link.label}>
                        <span className="text-sm text-muted-foreground/50">
                          {link.label}
                        </span>
                      </li>
                    ),
                  )}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-10 border-t border-border/40 pt-6">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground/60">
            Fonte pública: dados.cvm.gov.br · Operação read-only nesta fase
          </p>
        </div>
      </div>
    </footer>
  );
}
