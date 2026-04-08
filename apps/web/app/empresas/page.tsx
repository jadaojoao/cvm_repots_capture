import Link from "next/link";
import type { Metadata } from "next";

import { CompanyDirectoryFilters } from "@/components/companies/company-directory-filters";
import { CompanyDirectoryList } from "@/components/companies/company-directory-list";
import { DirectoryPagination } from "@/components/companies/directory-pagination";
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
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-16 sm:px-6">
        <Alert className="rounded-[1.5rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
          <AlertTitle>Diretorio temporariamente indisponivel</AlertTitle>
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
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-10">
      <div className="space-y-4">
        <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
          PG-02 - Hub de empresas
        </p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
              Diretorio publico de empresas
            </h1>
            <p className="max-w-3xl text-base leading-8 text-muted-foreground sm:text-lg">
              Use busca, setor canonico e paginacao para cair na companhia certa
              sem depender de navegacao lateral ou filtros client-side opacos.
            </p>
          </div>
          <p className="text-sm text-muted-foreground">
            {formatCompactInteger(directory.pagination.total_items)} resultados
          </p>
        </div>
      </div>

      {filtersError ? (
        <Alert className="rounded-[1.25rem] border border-border/70 bg-background/85 px-5 py-4">
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
    </div>
  );
}
