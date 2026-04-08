"use client";

import { useEffect } from "react";

import { getUserFacingErrorCopy } from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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

  const copy = getUserFacingErrorCopy(error);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-24 sm:px-6">
      <p className="text-xs uppercase tracking-[0.28em] text-muted-foreground">
        Erro de servico
      </p>
      <h1 className="font-heading text-4xl tracking-[-0.05em] text-foreground">
        {copy.title}
      </h1>
      <Alert className="rounded-[1.5rem] border border-destructive/25 bg-destructive/6 px-5 py-5 text-left">
        <AlertTitle>Falha controlada da camada web</AlertTitle>
        <AlertDescription>{copy.message}</AlertDescription>
      </Alert>
      <div>
        <Button size="lg" className="rounded-full px-5" onClick={() => reset()}>
          Tentar novamente
        </Button>
      </div>
    </div>
  );
}
