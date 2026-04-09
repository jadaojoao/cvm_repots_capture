import {
  fetchCompanyInfo,
  fetchCompanyKpis,
  fetchCompanyYears,
  getUserFacingErrorMessage,
  type CompanyInfo,
  type KPIBundle,
} from "./api.ts";
import {
  buildFeaturedCompareRows,
  hasComparableKpiValues,
  intersectYears,
  parseCompanyIdsCsv,
  type CompareCompanyBundle,
  type CompareKpiRow,
} from "./compare-utils.ts";
import { normalizeSelectedYears } from "./search-params.ts";

export type CompareCompanyOption = {
  cd_cvm: number;
  company_name: string;
  ticker_b3: string | null;
  sector_name: string;
};

export type ComparePageData = {
  selectedCompanies: CompareCompanyOption[];
  comparedCompanies: CompareCompanyOption[];
  availableYears: number[];
  selectedYears: number[];
  referenceYear: number | null;
  rows: CompareKpiRow[];
  dataError: string | null;
  partialErrors: string[];
};

type ComparePageLoaders = {
  fetchCompanyInfo?: (cdCvm: number) => Promise<CompanyInfo | null>;
  fetchCompanyYears?: (cdCvm: number) => Promise<number[]>;
  fetchCompanyKpis?: (cdCvm: number, years: number[]) => Promise<KPIBundle>;
};

type CompareYearCandidate = {
  company: CompanyInfo;
  years: number[];
};

function toCompareOption(company: CompanyInfo): CompareCompanyOption {
  return {
    cd_cvm: company.cd_cvm,
    company_name: company.company_name,
    ticker_b3: company.ticker_b3,
    sector_name: company.sector_name,
  };
}

const EMPTY_RESULT: ComparePageData = {
  selectedCompanies: [],
  comparedCompanies: [],
  availableYears: [],
  selectedYears: [],
  referenceYear: null,
  rows: [],
  dataError: null,
  partialErrors: [],
};

export async function loadComparePageData(
  rawIds: string | undefined,
  rawYears: string | undefined,
  loaders: ComparePageLoaders = {},
): Promise<ComparePageData> {
  const ids = parseCompanyIdsCsv(rawIds);
  if (ids.length === 0) {
    return EMPTY_RESULT;
  }

  const fetchInfo = loaders.fetchCompanyInfo ?? fetchCompanyInfo;
  const fetchYears = loaders.fetchCompanyYears ?? fetchCompanyYears;
  const fetchKpis = loaders.fetchCompanyKpis ?? fetchCompanyKpis;
  const partialErrors: string[] = [];
  const infoResults = await Promise.allSettled(ids.map((id) => fetchInfo(id)));

  const selectedCompanyInfo: CompanyInfo[] = [];

  infoResults.forEach((result, index) => {
    const requestedId = ids[index];

    if (result.status === "fulfilled") {
      if (result.value) {
        selectedCompanyInfo.push(result.value);
      } else {
        partialErrors.push(`Empresa ${requestedId} nao encontrada.`);
      }
      return;
    }

    partialErrors.push(getUserFacingErrorMessage(result.reason));
  });

  if (selectedCompanyInfo.length === 0) {
    return {
      ...EMPTY_RESULT,
      dataError: "Nao foi possivel carregar as empresas selecionadas.",
      partialErrors,
    };
  }

  const selectedCompanies = selectedCompanyInfo.map(toCompareOption);

  if (selectedCompanies.length < 2) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      partialErrors,
    };
  }

  const yearsResults = await Promise.allSettled(selectedCompanyInfo.map((company) => fetchYears(company.cd_cvm)));
  const yearCapableCompanies: CompareYearCandidate[] = [];

  yearsResults.forEach((result, index) => {
    const company = selectedCompanyInfo[index];

    if (result.status === "fulfilled") {
      if (result.value.length === 0) {
        partialErrors.push(`A empresa ${company.company_name} nao possui anos disponiveis.`);
        return;
      }
      yearCapableCompanies.push({
        company,
        years: result.value,
      });
      return;
    }

    partialErrors.push(
      `Nao foi possivel carregar os anos de ${company.company_name}: ${getUserFacingErrorMessage(result.reason)}`,
    );
  });

  const availableYears = intersectYears(
    yearCapableCompanies.map((entry) => entry.years),
  );
  const selectedYears = normalizeSelectedYears(availableYears, rawYears);

  if (yearCapableCompanies.length < 2) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      availableYears,
      selectedYears,
      partialErrors,
      dataError:
        "A comparacao precisa de pelo menos duas empresas com anos disponiveis para o mesmo fluxo.",
    };
  }

  if (availableYears.length === 0) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      availableYears,
      selectedYears,
      partialErrors,
      dataError:
        "As empresas selecionadas nao possuem anos em comum para comparacao. Ajuste a selecao.",
    };
  }

  if (selectedYears.length === 0) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      availableYears,
      selectedYears,
      partialErrors,
      dataError: "Nao foi possivel resolver um periodo valido para comparacao.",
    };
  }

  const kpiResults = await Promise.allSettled(
    yearCapableCompanies.map((entry) => fetchKpis(entry.company.cd_cvm, selectedYears)),
  );

  const comparedBundles: CompareCompanyBundle[] = [];

  kpiResults.forEach((result, index) => {
    const company = yearCapableCompanies[index].company;

    if (result.status === "fulfilled") {
      comparedBundles.push({
        company,
        bundle: result.value,
      });
      return;
    }

    partialErrors.push(
      `Nao foi possivel carregar os KPIs de ${company.company_name}: ${getUserFacingErrorMessage(result.reason)}`,
    );
  });

  if (comparedBundles.length < 2) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      availableYears,
      selectedYears,
      partialErrors,
      dataError:
        "A comparacao precisa de pelo menos duas empresas com dados de KPI disponiveis no periodo.",
    };
  }

  const referenceYear = selectedYears[selectedYears.length - 1] ?? null;
  const rows =
    referenceYear === null
      ? []
      : buildFeaturedCompareRows(comparedBundles, referenceYear);

  if (!hasComparableKpiValues(rows)) {
    return {
      ...EMPTY_RESULT,
      selectedCompanies,
      comparedCompanies: comparedBundles.map((entry) => toCompareOption(entry.company)),
      availableYears,
      selectedYears,
      referenceYear,
      partialErrors,
      dataError:
        "Os KPIs anuais deste recorte nao possuem valores comparaveis para a selecao atual.",
    };
  }

  return {
    ...EMPTY_RESULT,
    selectedCompanies,
    comparedCompanies: comparedBundles.map((entry) => toCompareOption(entry.company)),
    availableYears,
    selectedYears,
    referenceYear,
    rows,
    partialErrors,
  };
}
