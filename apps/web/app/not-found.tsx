import Link from "next/link";

import {
  InfoChip,
  PageShell,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <PageShell density="relaxed" className="max-w-4xl text-center">
      <SurfaceCard
        tone="hero"
        padding="hero"
        className="items-center text-center"
      >
        <InfoChip tone="muted">404 - rota nao encontrada</InfoChip>
        <SectionHeading
          title="Esse caminho ainda nao existe nesta fase."
          titleAs="h1"
          description="O slice atual cobre a home, o diretorio de empresas, a comparacao, o detalhe por companhia e a leitura por setores. KPIs e macro entram nas proximas fases."
          bodyClassName="mx-auto max-w-2xl"
          descriptionClassName="mx-auto"
        />
        <div className="flex flex-wrap justify-center gap-3">
          <Link
            href="/"
            className={cn(buttonVariants({ size: "lg" }), "rounded-full px-5")}
          >
            Voltar para a home
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
