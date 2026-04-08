import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-24 text-center sm:px-6">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
        404 · rota não encontrada
      </p>
      <h1 className="font-heading text-5xl tracking-[-0.06em] text-foreground">
        Esse caminho ainda não existe nesta fase.
      </h1>
      <p className="mx-auto max-w-2xl text-base leading-8 text-muted-foreground">
        O slice atual cobre a home, o diretório de empresas e o detalhe por
        companhia. Rotas de comparação, setores, KPIs e macro entram nas próximas
        fases.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <Link
          href="/"
          className={cn(buttonVariants({ size: "lg" }), "rounded-full px-5")}
        >
          Voltar para a home
        </Link>
        <Link
          href="/empresas"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-full px-5")}
        >
          Abrir empresas
        </Link>
      </div>
    </div>
  );
}
