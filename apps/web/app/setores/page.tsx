import Link from "next/link";
import type { Metadata } from "next";

import { SectorDirectoryList } from "@/components/sectors/sector-directory-list";
import { SectorHubTracker } from "@/components/sectors/sector-hub-tracker";
import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { formatCompactInteger } from "@/lib/formatters";
import { loadSectorsPageData } from "@/lib/sectors-page-data";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "Setores",
  description:
    "Hub setorial da V2 web com leitura agregada por setor, contagem de empresas e snapshots anuais.",
};

export const dynamic = "force-dynamic";

export default async function SetoresPage() {
  const { directory, directoryError } = await loadSectorsPageData();

  if (!directory) {
    return (
      <PageShell density="relaxed" className="max-w-4xl">
        <SurfaceCard tone="hero" padding="hero" className="space-y-6">
          <SectionHeading
            eyebrow="PG-05 - Hub de setores"
            title="Leitura setorial temporariamente indisponivel"
            titleAs="h1"
            description="O hub de setores nao respondeu agora. O restante da navegacao publica continua disponivel."
          />
          <Alert className="rounded-[1.75rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
            <AlertTitle>Falha controlada do hub setorial</AlertTitle>
            <AlertDescription>
              {directoryError ??
                "Nao foi possivel carregar os setores agora. Tente novamente em instantes."}
            </AlertDescription>
          </Alert>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/setores"
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

  const totalCompanies = directory.items.reduce(
    (accumulator, item) => accumulator + item.company_count,
    0,
  );

  return (
    <PageShell density="default">
      <SectorHubTracker sectorCount={directory.items.length} />

      <SectionHeading
        eyebrow="PG-05 - Hub de setores"
        title="Leitura por setores"
        titleAs="h1"
        description="Entre por cadeias produtivas e clusters analiticos para sair da navegacao empresa a empresa quando o problema e tematico."
        meta={
          <div className="flex flex-wrap items-center gap-2">
            <InfoChip tone="muted">
              {formatCompactInteger(directory.items.length)} setores
            </InfoChip>
            <InfoChip tone="muted">
              {formatCompactInteger(totalCompanies)} empresas somadas
            </InfoChip>
          </div>
        }
      />

      <SurfaceCard tone="subtle" padding="lg" className="space-y-4">
        <p className="text-sm leading-7 text-muted-foreground">
          Cada card entrega um snapshot do ano mais recente disponivel no setor,
          mantendo metricas ausentes como lacunas explicitas em vez de
          preenchimento artificial.
        </p>
      </SurfaceCard>

      <SectorDirectoryList items={directory.items} />
    </PageShell>
  );
}
