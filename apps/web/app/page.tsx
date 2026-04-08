import { ArrowUpRightIcon } from "lucide-react";

import { CompanySearchHero } from "@/components/home/company-search-hero";
import { FutureDomainGrid } from "@/components/home/future-domain-grid";
import { TrustStrip } from "@/components/home/trust-strip";
import { Badge } from "@/components/ui/badge";
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
    <div className="pb-18">
      <section className="mx-auto flex w-full max-w-7xl flex-col gap-12 px-4 pb-14 pt-14 sm:px-6 lg:px-10 lg:pb-20 lg:pt-18">
        <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="space-y-8">
            <div className="flex flex-wrap items-center gap-3">
              <Badge className="rounded-full bg-background px-3 py-1 text-[0.68rem] uppercase tracking-[0.24em] text-foreground shadow-sm shadow-black/5">
                V2 web · slice público
              </Badge>
              <span className="text-xs uppercase tracking-[0.24em] text-muted-foreground">
                Home → Empresas → Empresa
              </span>
            </div>

            <CompanySearchHero
              apiAvailable={health?.status === "ok"}
              totalCompanies={totalCompanies}
            />
          </div>

          <aside className="flex flex-col gap-5 border-t border-border/60 pt-6 xl:border-l xl:border-t-0 xl:pl-8 xl:pt-2">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
                Leitura orientada a descoberta
              </p>
              <h2 className="font-heading text-2xl leading-tight text-foreground">
                Menos fricção para encontrar a empresa certa.
              </h2>
            </div>

            <div className="space-y-4 text-sm leading-7 text-muted-foreground">
              <p>
                A fase atual evita dashboards genéricos e entra pela tarefa
                principal: descobrir, abrir e analisar uma companhia em poucos
                passos.
              </p>
              <p>
                O backend já sustenta busca, diretório paginado, filtros
                canônicos, detalhe rico, KPIs e demonstrações.
              </p>
            </div>

            <div className="space-y-2 border-t border-border/60 pt-5 text-sm text-muted-foreground">
              <p className="flex items-center justify-between">
                <span>Empresas com dados</span>
                <span className="font-medium text-foreground">
                  {formatCompactInteger(totalCompanies)}
                </span>
              </p>
              <p className="flex items-center justify-between">
                <span>Status da API</span>
                <span className="font-medium text-foreground">
                  {health?.status === "ok" ? "Pronta" : "Indisponível"}
                </span>
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-muted-foreground">
              Próximas superfícies
              <ArrowUpRightIcon className="size-3.5" />
            </div>
          </aside>
        </div>

        <FutureDomainGrid />
      </section>
      <TrustStrip health={health} totalCompanies={totalCompanies} />
    </div>
  );
}
