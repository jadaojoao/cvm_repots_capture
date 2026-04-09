import Link from "next/link";
import type { Metadata } from "next";

import { CompareKpiTable } from "@/components/compare/compare-kpi-table";
import { CompareSelector } from "@/components/compare/compare-selector";
import { CompareTracker } from "@/components/compare/compare-tracker";
import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { fetchCompanies } from "@/lib/api";
import {
  loadComparePageData,
  type CompareCompanyOption,
  type ComparePageData,
} from "@/lib/compare-page-data";
import { getFirstParam } from "@/lib/search-params";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Comparar",
  description:
    "Comparacao lado a lado de empresas com base nos KPIs anuais da API V2.",
};

export const dynamic = "force-dynamic";

type ComparePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

function toQuickOption(item: {
  cd_cvm: number;
  company_name: string;
  ticker_b3: string | null;
  sector_name: string;
}): CompareCompanyOption {
  return {
    cd_cvm: item.cd_cvm,
    company_name: item.company_name,
    ticker_b3: item.ticker_b3,
    sector_name: item.sector_name,
  };
}

function getComparisonStateCopy(compareData: ComparePageData): {
  title: string;
  description: string;
} | null {
  if (compareData.selectedCompanies.length < 2 || !compareData.dataError) {
    return null;
  }

  if (compareData.availableYears.length === 0) {
    return {
      title: "Sem periodo em comum",
      description:
        "A selecao atual nao chegou a um recorte anual comum. Ajuste as empresas ou volte ao diretorio para montar outra combinacao.",
    };
  }

  if (compareData.comparedCompanies.length < 2) {
    return {
      title: "Dados insuficientes para comparar",
      description:
        "A pagina manteve a selecao atual, mas ainda faltam ao menos duas empresas com dados validos para o periodo resolvido.",
    };
  }

  return {
    title: "Comparacao precisa de ajuste",
    description:
      "Os dados foram carregados, mas este recorte ainda nao produz uma tabela comparavel util. Ajuste o periodo ou a combinacao de empresas.",
  };
}

export default async function ComparePage({ searchParams }: ComparePageProps) {
  const resolvedSearchParams = await searchParams;
  const ids = getFirstParam(resolvedSearchParams.ids);
  const years = getFirstParam(resolvedSearchParams.anos);

  const [compareData, quickPayload] = await Promise.all([
    loadComparePageData(ids, years),
    fetchCompanies({ page: 1, pageSize: 8 }).catch(() => null),
  ]);

  const quickCompanies = (quickPayload?.items ?? []).map(toQuickOption);
  const saneQuickCompanies = quickCompanies.filter(
    (company) =>
      Number.isFinite(company.cd_cvm) &&
      company.cd_cvm > 0 &&
      company.company_name.trim() !== "--",
  );
  const comparisonState = getComparisonStateCopy(compareData);
  const partialErrorDescription =
    compareData.partialErrors.length === 0
      ? null
      : [
          compareData.partialErrors.slice(0, 3).join(" "),
          compareData.comparedCompanies.length >= 2 &&
          compareData.comparedCompanies.length < compareData.selectedCompanies.length
            ? `A tabela abaixo usa ${compareData.comparedCompanies.length} empresas com dados completos para o periodo.`
            : null,
        ]
          .filter(Boolean)
          .join(" ");

  return (
    <PageShell density="default">
      <CompareTracker
        companyIds={compareData.selectedCompanies.map((company) => company.cd_cvm)}
        years={compareData.selectedYears}
        comparableCompanies={compareData.comparedCompanies.length}
      />

      <SectionHeading
        eyebrow="PG-04 - Comparar"
        title="Comparacao de empresas"
        titleAs="h1"
        description="Monte uma comparacao lado a lado com empresas da base e use a primeira selecao como referencia de deltas."
        meta={
          <InfoChip tone="muted">
            {compareData.comparedCompanies.length >= 2
              ? `${compareData.comparedCompanies.length} empresas comparaveis`
              : "Selecione ao menos 2 empresas"}
          </InfoChip>
        }
      />

      <CompareSelector
        pathname="/comparar"
        selectedCompanies={compareData.selectedCompanies}
        quickCompanies={saneQuickCompanies}
        availableYears={compareData.availableYears}
        selectedYears={compareData.selectedYears}
      />

      {compareData.dataError ? (
        <Alert className="rounded-[1.75rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
          <AlertTitle>Comparacao indisponivel no estado atual</AlertTitle>
          <AlertDescription>{compareData.dataError}</AlertDescription>
        </Alert>
      ) : null}

      {compareData.partialErrors.length > 0 ? (
        <Alert className="rounded-[1.75rem] border border-border/70 bg-background/85 px-5 py-4 text-left">
          <AlertTitle>Alguns dados nao puderam ser carregados</AlertTitle>
          <AlertDescription>{partialErrorDescription}</AlertDescription>
        </Alert>
      ) : null}

      {compareData.selectedCompanies.length < 2 ? (
        <SurfaceCard tone="muted" padding="hero" className="space-y-5">
          <SectionHeading
            eyebrow="Passo inicial"
            title="Selecione ao menos duas empresas"
            titleAs="h2"
            description="Use a busca da comparacao ou entre pelo diretorio de empresas para montar a primeira analise lado a lado."
            descriptionClassName="text-sm leading-7"
          />
          <div className="flex flex-wrap gap-3">
            <Link
              href="/empresas"
              className={cn(
                buttonVariants({ size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Abrir diretorio
            </Link>
            <Link
              href="/"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Voltar para home
            </Link>
          </div>
        </SurfaceCard>
      ) : null}

      {comparisonState ? (
        <SurfaceCard
          tone="muted"
          padding="hero"
          className="space-y-5"
          data-testid="compare-state-card"
        >
          <SectionHeading
            eyebrow="Estado atual"
            title={comparisonState.title}
            titleAs="h2"
            description={comparisonState.description}
            descriptionClassName="text-sm leading-7"
          />
          <div className="flex flex-wrap gap-3">
            <Link
              href="/comparar"
              className={cn(
                buttonVariants({ size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Reiniciar comparacao
            </Link>
            <Link
              href="/empresas"
              className={cn(
                buttonVariants({ variant: "outline", size: "lg" }),
                "rounded-full px-5",
              )}
            >
              Escolher outras empresas
            </Link>
          </div>
        </SurfaceCard>
      ) : null}

      {compareData.comparedCompanies.length >= 2 &&
      compareData.referenceYear !== null &&
      compareData.rows.length > 0 &&
      !compareData.dataError ? (
        <CompareKpiTable
          companies={compareData.comparedCompanies}
          rows={compareData.rows}
          referenceYear={compareData.referenceYear}
        />
      ) : null}
    </PageShell>
  );
}
