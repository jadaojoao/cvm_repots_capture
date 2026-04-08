import { ArrowUpRightIcon } from "lucide-react";

import { CompanySearchHero } from "@/components/home/company-search-hero";
import { FutureDomainGrid } from "@/components/home/future-domain-grid";
import { TrustStrip } from "@/components/home/trust-strip";
import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { fetchCompanies, safeFetchHealth } from "@/lib/api";
import { formatCompactInteger } from "@/lib/formatters";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [health, companySnapshot] = await Promise.all([
    safeFetchHealth(),
    fetchCompanies({ page: 1, pageSize: 1 }).catch(() => null),
  ]);

  const totalCompanies = companySnapshot?.pagination.total_items ?? null;

  return (
    <>
      <PageShell density="relaxed" className="pb-18">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.15fr)_22rem]">
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-3">
              <InfoChip tone="brand">V2 web - slice publico</InfoChip>
              <InfoChip>Home - Empresas - Empresa</InfoChip>
            </div>

            <CompanySearchHero
              apiAvailable={health?.status === "ok"}
              totalCompanies={totalCompanies}
            />
          </div>

          <SurfaceCard
            tone="subtle"
            padding="lg"
            className="flex flex-col justify-between gap-8"
          >
            <div className="space-y-4">
              <SectionHeading
                eyebrow="Leitura orientada a descoberta"
                title="Menos friccao para encontrar a empresa certa."
                titleAs="h2"
                description="A fase atual evita dashboards genericos e entra pela tarefa principal: descobrir, abrir e analisar uma companhia em poucos passos."
                bodyClassName="max-w-none"
                descriptionClassName="text-base leading-7"
              />
              <p className="text-sm leading-7 text-muted-foreground">
                O backend ja sustenta busca, diretorio paginado, filtros
                canonicos, detalhe rico, KPIs e demonstracoes.
              </p>
            </div>

            <div className="space-y-5 border-t border-border/55 pt-5">
              <div className="grid gap-3">
                <p className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Empresas com dados</span>
                  <span className="font-medium text-foreground">
                    {formatCompactInteger(totalCompanies)}
                  </span>
                </p>
                <p className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>Status da API</span>
                  <span className="font-medium text-foreground">
                    {health?.status === "ok" ? "Pronta" : "Indisponivel"}
                  </span>
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Proximas superficies
                <ArrowUpRightIcon className="size-3.5" />
              </div>
            </div>
          </SurfaceCard>
        </div>

        <FutureDomainGrid />
      </PageShell>

      <TrustStrip health={health} totalCompanies={totalCompanies} />
    </>
  );
}
