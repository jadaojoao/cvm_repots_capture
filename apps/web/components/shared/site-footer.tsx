export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-background/80">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-10 sm:px-6 lg:px-10">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <p className="font-heading text-lg text-foreground">
              Leitura pública, rápida e rastreável dos dados financeiros da CVM.
            </p>
            <p className="mt-2 text-sm leading-7 text-muted-foreground">
              A V2 web nasce como camada read-only sobre a API estabilizada. Fluxos
              de refresh, comparação e domínios setoriais entram nas próximas fases.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm text-muted-foreground sm:grid-cols-4">
            <span>Metodologia</span>
            <span>Fontes</span>
            <span>Glossário</span>
            <span>Privacidade</span>
          </div>
        </div>
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground/80">
          Fonte pública: dados.cvm.gov.br · Operação read-only nesta fase
        </p>
      </div>
    </footer>
  );
}
