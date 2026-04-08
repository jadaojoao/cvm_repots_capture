import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CompanyDetailTracker } from "@/components/company/company-detail-tracker";
import { CompanyHeader } from "@/components/company/company-header";
import { CompanyOverview } from "@/components/company/company-overview";
import { CompanyStatements } from "@/components/company/company-statements";
import { CompanyUrlTabs } from "@/components/company/company-url-tabs";
import { CompanyYearSelector } from "@/components/company/company-year-selector";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import {
  fetchCompanyInfo,
  fetchCompanyKpis,
  fetchCompanyStatement,
  fetchCompanyYears,
} from "@/lib/api";
import { DETAIL_TABS, STATEMENT_OPTIONS } from "@/lib/constants";
import {
  coerceDetailTab,
  coerceStatement,
  getFirstParam,
  normalizeSelectedYears,
} from "@/lib/search-params";
import { cn } from "@/lib/utils";

type EmpresaDetailPageProps = {
  params: Promise<{ cd_cvm: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: EmpresaDetailPageProps): Promise<Metadata> {
  const { cd_cvm } = await params;
  const company = await fetchCompanyInfo(Number(cd_cvm)).catch(() => null);

  if (!company) {
    return {
      title: "Empresa não encontrada",
    };
  }

  return {
    title: company.company_name,
    description: `Leitura detalhada de ${company.company_name} com KPIs anuais, seleção de anos e demonstrações financeiras da CVM.`,
  };
}

export default async function EmpresaDetailPage({
  params,
  searchParams,
}: EmpresaDetailPageProps) {
  const { cd_cvm } = await params;
  const resolvedSearchParams = await searchParams;
  const cdCvm = Number(cd_cvm);
  const pathname = `/empresas/${cdCvm}`;

  const company = await fetchCompanyInfo(cdCvm);
  if (!company) {
    notFound();
  }

  const availableYears = await fetchCompanyYears(cdCvm);
  if (availableYears.length === 0) {
    notFound();
  }

  const currentTab = coerceDetailTab(getFirstParam(resolvedSearchParams.aba));
  const currentStatement = coerceStatement(getFirstParam(resolvedSearchParams.stmt));
  const selectedYears = normalizeSelectedYears(
    availableYears,
    getFirstParam(resolvedSearchParams.anos),
  );

  let bundle = null;
  let statement = null;
  let errorMessage: string | null = null;

  try {
    [bundle, statement] = await Promise.all([
      fetchCompanyKpis(cdCvm, selectedYears),
      fetchCompanyStatement(cdCvm, selectedYears, currentStatement),
    ]);
  } catch (error) {
    errorMessage =
      error instanceof Error
        ? error.message
        : "Não foi possível carregar a leitura detalhada desta empresa.";
  }

  if (!bundle || !statement) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-16 sm:px-6">
        <Alert className="rounded-[1.5rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-sm leading-7 text-destructive">
          {errorMessage ?? "Não foi possível carregar a leitura detalhada desta empresa."}
        </Alert>
        <Link
          href="/empresas"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "w-fit rounded-full px-5")}
        >
          Voltar para o diretório
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-10">
      <CompanyDetailTracker
        cdCvm={company.cd_cvm}
        companyName={company.company_name}
        years={selectedYears}
        tab={currentTab}
        statementType={currentStatement}
      />

      <CompanyHeader company={company} selectedYears={selectedYears} />

      <section className="flex flex-col gap-4 rounded-[1.5rem] border border-border/70 bg-background/90 px-5 py-5 shadow-sm shadow-black/5">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
              Filtro temporal
            </p>
            <p className="text-sm leading-7 text-muted-foreground">
              Quando nenhum parâmetro é informado, a página usa os três anos mais
              recentes disponíveis.
            </p>
          </div>
          <CompanyYearSelector
            pathname={pathname}
            availableYears={availableYears}
            selectedYears={selectedYears}
          />
        </div>
      </section>

      <CompanyUrlTabs
        pathname={pathname}
        currentValue={currentTab}
        paramName="aba"
        options={Array.from(DETAIL_TABS)}
      />

      {currentTab === "visao-geral" ? (
        <CompanyOverview bundle={bundle} />
      ) : (
        <div className="space-y-6">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
              Tipo de demonstração
            </p>
            <CompanyUrlTabs
              pathname={pathname}
              currentValue={currentStatement}
              paramName="stmt"
              options={Array.from(STATEMENT_OPTIONS)}
              eventName="company_statement_changed"
            />
          </div>
          <CompanyStatements matrix={statement} />
        </div>
      )}
    </div>
  );
}
