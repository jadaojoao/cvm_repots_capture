import {
  fetchCompanies,
  fetchCompanyFilters,
  getUserFacingErrorMessage,
  type CompanyDirectoryPage,
  type CompanyFiltersResponse,
} from "./api.ts";

type CompaniesPageLoaders = {
  fetchDirectory?: () => Promise<CompanyDirectoryPage>;
  fetchFilters?: () => Promise<CompanyFiltersResponse>;
};

export type CompaniesPageData = {
  directory: CompanyDirectoryPage | null;
  filters: CompanyFiltersResponse | null;
  directoryError: string | null;
  filtersError: string | null;
};

export async function loadCompaniesPageData(
  params: {
    search: string;
    sector: string | null;
    page: number;
    pageSize: number;
  },
  loaders: CompaniesPageLoaders = {},
): Promise<CompaniesPageData> {
  const fetchDirectory =
    loaders.fetchDirectory ??
    (() =>
      fetchCompanies({
        search: params.search,
        sector: params.sector,
        page: params.page,
        pageSize: params.pageSize,
      }));
  const fetchFilters = loaders.fetchFilters ?? (() => fetchCompanyFilters());

  const [directoryResult, filtersResult] = await Promise.allSettled([
    fetchDirectory(),
    fetchFilters(),
  ]);

  return {
    directory:
      directoryResult.status === "fulfilled" ? directoryResult.value : null,
    filters: filtersResult.status === "fulfilled" ? filtersResult.value : null,
    directoryError:
      directoryResult.status === "rejected"
        ? getUserFacingErrorMessage(directoryResult.reason)
        : null,
    filtersError:
      filtersResult.status === "rejected"
        ? getUserFacingErrorMessage(filtersResult.reason)
        : null,
  };
}
