import Link from "next/link";
import type { Metadata } from "next";

import { CompanyDirectoryFilters } from "@/components/companies/company-directory-filters";
import { CompanyDirectoryList } from "@/components/companies/company-directory-list";
import { DirectoryPagination } from "@/components/companies/directory-pagination";
import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { formatCompactInteger } from "@/lib/formatters";
import { loadCompaniesPageData } from "@/lib/companies-page-data";
import { coercePositiveInt, getFirstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Empresas",
  description:
    "Diretorio publico e paginado de empresas com dados financeiros ja processados na base CVM Analytics.",
};

export const dynamic = "force-dynamic";

type EmpresasPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function EmpresasPage({
  searchParams,
}: EmpresasPageProps) {
  const resolvedSearchParams = await searchParams;
  const currentSearch = getFirstParam(resolvedSearchParams.busca) ?? "";
  const currentSector = getFirstParam(resolvedSearchParams.setor) ?? null;
  const currentPage = coercePositiveInt(
    getFirstParam(resolvedSearchParams.pagina),
    1,
  );
  const retryParams = new URLSearchParams();
  if (currentSearch) {
    retryParams.set("busca", currentSearch);
  }
  if (currentSector) {
    retryParams.set("setor", currentSector);
  }
  if (currentPage > 1) {
    retryParams.set("pagina", String(currentPage));
  }
  const retryQuery = retryParams.toString();
  const retryHref = retryQuery ? `/empresas?${retryQuery}` : "/empresas";

  const { directory, filters, directoryError, filtersError } =
    await loadCompaniesPageData({
      search: currentSearch,
      sector: currentSector,
      page: currentPage,
      pageSize: 20,
    });

  if (!directory) {
    return (
      <PageShell density="relaxed" className="max-w-4xl">
        <SurfaceCard tone="hero" padding="hero" className="space-y-6">
          <SectionHeading
            eyebrow="PG-02 - Hub de empresas"
            title="Diretorio temporariamente indisponivel"
            titleAs="h1"
            description="A listagem de empresas nao respondeu agora. O fluxo de busca e navegacao pode ser retomado assim que a API voltar a responder."
          />
          <Alert className="rounded-[1.75rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
            <AlertTitle>Falha controlada da listagem</AlertTitle>
            <AlertDescription>
              {directoryError ??
                "Nao foi possivel carregar o diretorio de empresas agora. Tente novamente em instantes."}
            </AlertDescription>
          </Alert>
          <div className="flex flex-wrap gap-3">
            <Link
              href={retryHref}
              className={cn(buttonVariants({ size: "lg" }), "rounded-full px-5")}
            >
              Tentar novamente
            </Link>
            <Link
              href="/"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Voltar para a home
            </Link>
          </div>
        </SurfaceCard>
      </PageShell>
    );
  }

  return (
    <PageShell density="default">
      <SectionHeading
        eyebrow="PG-02 - Hub de empresas"
        title="Diretorio publico de empresas"
        titleAs="h1"
        description="Use busca, setor canonico e paginacao para cair na companhia certa sem depender de navegacao lateral ou filtros client-side opacos."
        meta={
          <InfoChip tone="muted">
            {formatCompactInteger(directory.pagination.total_items)} resultados
          </InfoChip>
        }
      />

      {filtersError ? (
        <Alert className="rounded-[1.75rem] border border-border/70 bg-background/85 px-5 py-4">
          <AlertTitle>Filtro setorial indisponivel</AlertTitle>
          <AlertDescription>
            {filtersError} A busca livre e a paginacao continuam disponiveis.
          </AlertDescription>
        </Alert>
      ) : null}

      <CompanyDirectoryFilters
        currentSearch={currentSearch}
        currentSector={currentSector}
        sectors={filters?.sectors ?? []}
        sectorFilterUnavailable={Boolean(filtersError)}
      />

      <CompanyDirectoryList items={directory.items} />

      <DirectoryPagination
        currentPage={directory.pagination.page}
        totalPages={directory.pagination.total_pages}
        hasNext={directory.pagination.has_next}
        hasPrevious={directory.pagination.has_previous}
        currentSearch={currentSearch}
        currentSector={Boolean(filtersError) ? null : currentSector}
      />
    </PageShell>
  );
}
