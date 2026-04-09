import Link from "next/link";
import type { Metadata } from "next";
import { ChevronRightIcon } from "lucide-react";
import { notFound } from "next/navigation";

import { SectorCompanyTable } from "@/components/sectors/sector-company-table";
import { SectorDetailTracker } from "@/components/sectors/sector-detail-tracker";
import { SectorOverview } from "@/components/sectors/sector-overview";
import { SectorUrlTabs } from "@/components/sectors/sector-url-tabs";
import { SectorYearSelector } from "@/components/sectors/sector-year-selector";
import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { fetchSectorDetail } from "@/lib/api";
import { formatCompactInteger } from "@/lib/formatters";
import { getFirstParam } from "@/lib/search-params";
import { loadSectorDetailPageData } from "@/lib/sectors-page-data";
import { cn } from "@/lib/utils";

type SectorDetailPageProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const SECTOR_TABS = [
  { value: "visao-geral", label: "Visao Geral" },
  { value: "empresas", label: "Empresas" },
] as const;

export const dynamic = "force-dynamic";

function SectorDetailError({
  message,
}: {
  message: string;
}) {
  return (
    <PageShell density="relaxed" className="max-w-4xl">
      <SurfaceCard tone="hero" padding="hero" className="space-y-6">
        <SectionHeading
          eyebrow="PG-06 - Detalhe do setor"
          title="Leitura setorial indisponivel"
          titleAs="h1"
          description="O detalhe do setor nao conseguiu concluir a leitura agora."
        />
        <Alert className="rounded-[1.75rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
          <AlertTitle>Falha controlada do detalhe setorial</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/setores"
            className={cn(buttonVariants({ size: "lg" }), "rounded-full px-5")}
          >
            Voltar para setores
          </Link>
          <Link
            href="/empresas"
            className={cn(
              buttonVariants({ variant: "outline", size: "lg" }),
              "rounded-full px-5",
            )}
          >
            Abrir empresas
          </Link>
        </div>
      </SurfaceCard>
    </PageShell>
  );
}

export async function generateMetadata({
  params,
}: SectorDetailPageProps): Promise<Metadata> {
  const { slug } = await params;

  try {
    const detail = await fetchSectorDetail(slug);

    if (!detail) {
      return {
        title: "Setor nao encontrado",
      };
    }

    return {
      title: detail.sector_name,
      description: `Leitura setorial de ${detail.sector_name} com serie anual agregada e ranking anual de empresas.`,
    };
  } catch {
    return {
      title: "Leitura setorial indisponivel",
    };
  }
}

export default async function SectorDetailPage({
  params,
  searchParams,
}: SectorDetailPageProps) {
  const { slug } = await params;
  const resolvedSearchParams = await searchParams;
  const rawYear = getFirstParam(resolvedSearchParams.ano);
  const rawTab = getFirstParam(resolvedSearchParams.aba);
  const pathname = `/setores/${slug}`;

  const { detail, currentTab, detailError } = await loadSectorDetailPageData(
    slug,
    rawYear,
    rawTab,
  );

  if (!detail) {
    if (!detailError) {
      notFound();
    }

    return <SectorDetailError message={detailError} />;
  }

  return (
    <PageShell density="default">
      <SectorDetailTracker
        sectorSlug={detail.sector_slug}
        sectorName={detail.sector_name}
        selectedYear={detail.selected_year}
        companyCount={detail.company_count}
      />

      <div className="space-y-5">
        <nav aria-label="breadcrumb">
          <ol className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <li>
              <Link href="/" className="hover:text-foreground">
                Home
              </Link>
            </li>
            <li className="flex items-center gap-2">
              <ChevronRightIcon className="size-4" />
              <Link href="/setores" className="hover:text-foreground">
                Setores
              </Link>
            </li>
            <li className="flex items-center gap-2 text-foreground">
              <ChevronRightIcon className="size-4 text-muted-foreground" />
              <span>{detail.sector_name}</span>
            </li>
          </ol>
        </nav>

        <SurfaceCard tone="default" padding="lg">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <InfoChip tone="brand">PG-06 - Detalhe do setor</InfoChip>
                <InfoChip>{formatCompactInteger(detail.company_count)} empresas</InfoChip>
                <InfoChip tone="muted">Base {detail.selected_year}</InfoChip>
              </div>

              <div className="space-y-3">
                <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
                  {detail.sector_name}
                </h1>
                <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
                  O detalhe setorial combina leitura agregada por ano e ranking
                  anual de empresas, sempre sobre o mesmo slug canonico da API V2.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href={`/empresas?setor=${detail.sector_slug}`}
                className={cn(
                  buttonVariants({ variant: "outline", size: "lg" }),
                  "rounded-full px-5",
                )}
              >
                Filtrar empresas deste setor
              </Link>
            </div>
          </div>
        </SurfaceCard>
      </div>

      <SurfaceCard tone="subtle" padding="md" className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
              Recorte anual
            </p>
            <p className="text-sm leading-7 text-muted-foreground">
              Ano invalido ou ausente cai automaticamente para o periodo mais
              recente disponivel do setor.
            </p>
          </div>
          <SectorYearSelector
            pathname={pathname}
            sectorSlug={detail.sector_slug}
            availableYears={detail.available_years}
            selectedYear={detail.selected_year}
          />
        </div>
      </SurfaceCard>

      <SectorUrlTabs
        pathname={pathname}
        currentValue={currentTab}
        options={Array.from(SECTOR_TABS)}
      />

      {currentTab === "visao-geral" ? (
        <SectorOverview detail={detail} />
      ) : (
        <SectorCompanyTable
          companies={detail.companies}
          sectorSlug={detail.sector_slug}
          selectedYear={detail.selected_year}
        />
      )}
    </PageShell>
  );
}
