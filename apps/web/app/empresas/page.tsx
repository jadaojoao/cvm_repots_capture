import Link from "next/link";
import type { Metadata } from "next";

import { CompanyDirectoryFilters } from "@/components/companies/company-directory-filters";
import { CompanyDirectoryList } from "@/components/companies/company-directory-list";
import { DirectoryPagination } from "@/components/companies/directory-pagination";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { fetchCompanies, fetchCompanyFilters } from "@/lib/api";
import { formatCompactInteger } from "@/lib/formatters";
import { coercePositiveInt, getFirstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Empresas",
  description:
    "Diretório público e paginado de empresas com dados financeiros já processados na base CVM Analytics.",
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

  let directory = null;
  let filters = null;
  let errorMessage: string | null = null;

  try {
    [directory, filters] = await Promise.all([
      fetchCompanies({
        search: currentSearch,
        sector: currentSector,
        page: currentPage,
        pageSize: 20,
      }),
      fetchCompanyFilters(),
    ]);
  } catch (error) {
    errorMessage =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar o diretório de empresas.";
  }

  if (!directory || !filters) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-16 sm:px-6">
        <Alert className="rounded-[1.5rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-sm leading-7 text-destructive">
          {errorMessage ?? "Não foi possível carregar o diretório de empresas."}
        </Alert>
        <Link
          href="/"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "w-fit rounded-full px-5")}
        >
          Voltar para a home
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-10">
      <div className="space-y-4">
        <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
          PG-02 · Hub de empresas
        </p>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
              Diretório público de empresas
            </h1>
            <p className="max-w-3xl text-base leading-8 text-muted-foreground sm:text-lg">
              Use busca, setor canônico e paginação para cair na companhia certa
              sem depender de navegação lateral ou filtros client-side opacos.
            </p>
          </div>
          <p className="text-sm text-muted-foreground">
            {formatCompactInteger(directory.pagination.total_items)} resultados
          </p>
        </div>
      </div>

      <CompanyDirectoryFilters
        currentSearch={currentSearch}
        currentSector={currentSector}
        sectors={filters.sectors}
      />

      <CompanyDirectoryList items={directory.items} />

      <DirectoryPagination
        currentPage={directory.pagination.page}
        totalPages={directory.pagination.total_pages}
        hasNext={directory.pagination.has_next}
        hasPrevious={directory.pagination.has_previous}
        currentSearch={currentSearch}
        currentSector={currentSector}
      />
    </div>
  );
}
