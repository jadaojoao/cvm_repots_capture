"use client";

import Link from "next/link";
import { ArrowRightIcon, SearchIcon } from "lucide-react";
import { useDeferredValue, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CompanyDirectoryItem } from "@/lib/api";
import { formatCompactInteger, formatYearsLabel } from "@/lib/formatters";
import { track } from "@/lib/track";
import { cn } from "@/lib/utils";

type CompanySearchHeroProps = {
  apiAvailable: boolean;
  totalCompanies: number | null;
};

export function CompanySearchHero({
  apiAvailable,
  totalCompanies,
}: CompanySearchHeroProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<CompanyDirectoryItem[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const deferredQuery = useDeferredValue(query);

  useEffect(() => {
    const normalized = deferredQuery.trim();

    if (normalized.length < 2 || !apiAvailable) {
      setSuggestions([]);
      setSuggestionError(null);
      return;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      setLoadingSuggestions(true);
      setSuggestionError(null);

      try {
        const response = await fetch(
          `/api/company-search?q=${encodeURIComponent(normalized)}`,
          {
            cache: "no-store",
          },
        );
        const payload = (await response.json()) as {
          items?: CompanyDirectoryItem[];
          error?: string;
        };

        if (!active) {
          return;
        }

        if (!response.ok) {
          setSuggestions([]);
          setSuggestionError(payload.error ?? "Nao foi possivel buscar sugestoes.");
          return;
        }

        setSuggestions(payload.items ?? []);
      } catch {
        if (!active) {
          return;
        }
        setSuggestions([]);
        setSuggestionError("Nao foi possivel buscar sugestoes.");
      } finally {
        if (active) {
          setLoadingSuggestions(false);
        }
      }
    }, 180);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [apiAvailable, deferredQuery]);

  function navigateToDirectory(rawQuery: string) {
    const normalized = rawQuery.trim();
    const target = normalized
      ? `/empresas?busca=${encodeURIComponent(normalized)}`
      : "/empresas";

    track("home_search_submitted", {
      query: normalized,
    });

    startTransition(() => {
      router.push(target);
    });
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    navigateToDirectory(query);
  }

  function handleSuggestionSelection(item: CompanyDirectoryItem) {
    track("home_suggestion_selected", {
      cd_cvm: item.cd_cvm,
      company_name: item.company_name,
    });

    startTransition(() => {
      router.push(`/empresas/${item.cd_cvm}`);
    });
  }

  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-border/60 bg-background/90 px-6 py-8 shadow-[0_24px_70px_-38px_rgba(13,33,24,0.35)] backdrop-blur-xl sm:px-8 sm:py-10">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(183,110,44,0.16),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(25,78,55,0.12),_transparent_30%)]" />
      <div className="relative space-y-6">
        <div className="space-y-4">
          <Badge className="rounded-full bg-secondary px-3 py-1 text-[0.68rem] uppercase tracking-[0.2em] text-secondary-foreground">
            Descoberta orientada a analise
          </Badge>
          <div className="space-y-4">
            <h1 className="max-w-4xl font-heading text-4xl leading-[1.02] tracking-[-0.05em] text-foreground sm:text-5xl lg:text-6xl">
              Entre por empresa e va direto ao historico que importa.
            </h1>
            <p className="max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
              Busque companhias abertas pelo nome, ticker ou codigo CVM e caia
              direto em uma leitura publica, rapida e rastreavel dos numeros.
            </p>
          </div>
        </div>

        <form
          action="/empresas"
          className="space-y-4"
          method="get"
          onSubmit={handleSubmit}
        >
          <div className="relative">
            <div className="flex flex-col gap-3 rounded-[1.75rem] border border-border/70 bg-background/95 p-3 shadow-sm shadow-black/5 sm:flex-row sm:items-center">
              <div className="flex flex-1 items-center gap-3 rounded-[1.35rem] bg-muted/55 px-4 py-3">
                <SearchIcon className="size-4.5 text-muted-foreground" />
                <Input
                  name="busca"
                  type="search"
                  value={query}
                  placeholder="PETROBRAS, VALE3 ou 9512"
                  className="h-auto border-0 bg-transparent p-0 text-base shadow-none ring-0 focus-visible:ring-0"
                  onChange={(event) => setQuery(event.target.value)}
                  aria-label="Buscar empresa"
                />
              </div>
              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  type="submit"
                  className={cn(
                    buttonVariants({ size: "lg" }),
                    "rounded-[1.2rem] bg-primary px-5 text-primary-foreground hover:bg-primary/90",
                  )}
                  disabled={isPending || !apiAvailable}
                >
                  Buscar empresa
                  <ArrowRightIcon data-icon="inline-end" />
                </button>
                <Link
                  href="/empresas"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "lg" }),
                    "rounded-[1.2rem] px-5",
                  )}
                >
                  Ir para empresas
                </Link>
              </div>
            </div>

            {apiAvailable && (loadingSuggestions || suggestions.length > 0 || suggestionError) ? (
              <div className="absolute inset-x-0 top-[calc(100%+0.75rem)] z-20 overflow-hidden rounded-[1.5rem] border border-border/70 bg-background/98 shadow-[0_20px_50px_-35px_rgba(16,30,24,0.35)]">
                {loadingSuggestions ? (
                  <p className="px-5 py-4 text-sm text-muted-foreground">
                    Buscando sugestoes...
                  </p>
                ) : suggestionError ? (
                  <p className="px-5 py-4 text-sm text-destructive">{suggestionError}</p>
                ) : (
                  <ul className="divide-y divide-border/50">
                    {suggestions.map((item) => (
                      <li key={item.cd_cvm}>
                        <button
                          type="button"
                          className="flex w-full items-start justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/50"
                          onClick={() => handleSuggestionSelection(item)}
                        >
                          <div className="space-y-1">
                            <p className="font-medium text-foreground">
                              {item.company_name}
                            </p>
                            <p className="text-sm text-muted-foreground">
                              {item.ticker_b3 ?? "Sem ticker"} - CVM {item.cd_cvm}
                            </p>
                          </div>
                          <div className="space-y-1 text-right">
                            <p className="text-sm text-foreground">{item.sector_name}</p>
                            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
                              {formatYearsLabel(item.anos_disponiveis)}
                            </p>
                          </div>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : null}
          </div>
        </form>

        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/70 px-3 py-1.5">
            {apiAvailable ? "API pronta para busca" : "API indisponivel no momento"}
          </span>
          {totalCompanies !== null ? (
            <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/70 px-3 py-1.5">
              {formatCompactInteger(totalCompanies)} empresas com dados
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}
