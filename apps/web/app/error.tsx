"use client";

import { useEffect } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-24 sm:px-6">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
        Erro de serviço
      </p>
      <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground">
        A leitura web não conseguiu concluir esta solicitação.
      </h1>
      <Alert className="rounded-[1.5rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-sm leading-7 text-destructive">
        {error.message || "Tente novamente em instantes."}
      </Alert>
      <div>
        <Button size="lg" className="rounded-full px-5" onClick={() => reset()}>
          Tentar novamente
        </Button>
      </div>
    </div>
  );
}
