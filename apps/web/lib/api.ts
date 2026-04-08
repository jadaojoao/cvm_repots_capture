export type HealthResponse = {
  status: string;
  version: string;
  database_dialect: string | null;
  required_tables: string[];
  warnings: Array<{ severity: string; code: string; message: string; path: string | null }>;
  errors: Array<{ severity: string; code: string; message: string; path: string | null }>;
};

export type CompanyDirectoryItem = {
  cd_cvm: number;
  company_name: string;
  ticker_b3: string | null;
  setor_analitico: string | null;
  setor_cvm: string | null;
  sector_name: string;
  sector_slug: string;
  anos_disponiveis: number[];
  total_rows: number;
};

export type CompanyDirectoryPage = {
  items: CompanyDirectoryItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
  applied_filters: {
    search: string;
    sector: string | null;
  };
};

export type CompanySectorFilter = {
  sector_name: string;
  sector_slug: string;
  company_count: number;
};

export type CompanyFiltersResponse = {
  sectors: CompanySectorFilter[];
};

export type CompanyInfo = {
  cd_cvm: number;
  company_name: string;
  nome_comercial: string | null;
  cnpj: string | null;
  setor_cvm: string | null;
  setor_analitico: string | null;
  sector_name: string;
  sector_slug: string;
  company_type: string | null;
  ticker_b3: string | null;
};

export type TabularDataRow = Record<string, string | number | boolean | null>;

export type TabularData = {
  columns: string[];
  rows: TabularDataRow[];
};

export type KPIBundle = {
  cd_cvm: number;
  years: number[];
  annual: TabularData;
  quarterly: TabularData;
};

export type StatementMatrix = {
  cd_cvm: number;
  statement_type: string;
  years: number[];
  table: TabularData;
  exclude_conflicts: boolean;
};

type ApiErrorShape = {
  error?: {
    code?: string;
    message?: string;
  };
};

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "unknown_error",
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function getApiBaseUrl(): string {
  return (process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL).replace(/\/$/, "");
}

function buildApiUrl(path: string): string {
  return `${getApiBaseUrl()}${path}`;
}

async function toApiError(response: Response): Promise<ApiClientError> {
  let payload: ApiErrorShape | null = null;

  try {
    payload = (await response.json()) as ApiErrorShape;
  } catch {
    payload = null;
  }

  const message =
    payload?.error?.message ??
    `Falha ao consultar a API (${response.status}).`;

  return new ApiClientError(message, response.status, payload?.error?.code);
}

async function apiFetch<T>(
  path: string,
  options?: {
    allowNotFound?: boolean;
  },
): Promise<T | null> {
  const response = await fetch(buildApiUrl(path), {
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (options?.allowNotFound && response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  return (await response.json()) as T;
}

function buildQuery(
  params: Record<string, string | number | null | undefined>,
): string {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    query.set(key, String(value));
  });

  const search = query.toString();
  return search ? `?${search}` : "";
}

export async function fetchHealth(): Promise<HealthResponse> {
  return (await apiFetch<HealthResponse>("/health")) as HealthResponse;
}

export async function safeFetchHealth(): Promise<HealthResponse | null> {
  try {
    return await fetchHealth();
  } catch {
    return null;
  }
}

export async function fetchCompanies(params: {
  search?: string;
  sector?: string | null;
  page?: number;
  pageSize?: number;
}): Promise<CompanyDirectoryPage> {
  return (await apiFetch<CompanyDirectoryPage>(
    `/companies${buildQuery({
      search: params.search,
      sector: params.sector,
      page: params.page,
      page_size: params.pageSize,
    })}`,
  )) as CompanyDirectoryPage;
}

export async function fetchCompanyFilters(): Promise<CompanyFiltersResponse> {
  return (await apiFetch<CompanyFiltersResponse>(
    "/companies/filters",
  )) as CompanyFiltersResponse;
}

export async function fetchCompanyInfo(
  cdCvm: number,
): Promise<CompanyInfo | null> {
  return apiFetch<CompanyInfo>(`/companies/${cdCvm}`, {
    allowNotFound: true,
  });
}

export async function fetchCompanyYears(cdCvm: number): Promise<number[]> {
  return (await apiFetch<number[]>(`/companies/${cdCvm}/years`)) as number[];
}

export async function fetchCompanyKpis(
  cdCvm: number,
  years: number[],
): Promise<KPIBundle> {
  return (await apiFetch<KPIBundle>(
    `/companies/${cdCvm}/kpis${buildQuery({
      years: years.join(","),
    })}`,
  )) as KPIBundle;
}

export async function fetchCompanyStatement(
  cdCvm: number,
  years: number[],
  statementType: string,
): Promise<StatementMatrix> {
  return (await apiFetch<StatementMatrix>(
    `/companies/${cdCvm}/statements${buildQuery({
      stmt: statementType,
      years: years.join(","),
    })}`,
  )) as StatementMatrix;
}
