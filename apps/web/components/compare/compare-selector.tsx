"use client";

import Link from "next/link";
import { PlusIcon, SearchIcon, XIcon } from "lucide-react";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { InfoChip, SurfaceCard } from "@/components/shared/design-system-recipes";
import { ExcelDownloadButton } from "@/components/shared/excel-download-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { serializeCompanyIds } from "@/lib/compare-utils";
import type { CompanyDirectoryItem } from "@/lib/api";
import { formatYearsLabel } from "@/lib/formatters";
import type { CompareCompanyOption } from "@/lib/compare-page-data";
import { mergeSearchParams, serializeYears } from "@/lib/search-params";
import { track } from "@/lib/track";
import { cn } from "@/lib/utils";

type CompareSelectorProps = {
  pathname: string;
  selectedCompanies: CompareCompanyOption[];
  quickCompanies: CompareCompanyOption[];
  availableYears: number[];
  selectedYears: number[];
  maxCompanies?: number;
};

type SuggestionResponse = {
  items?: CompanyDirectoryItem[];
  error?: string;
};

const DEFAULT_MAX_COMPANIES = 5;

function toCompareOption(item: CompanyDirectoryItem): CompareCompanyOption {
  return {
    cd_cvm: item.cd_cvm,
    company_name: item.company_name,
    ticker_b3: item.ticker_b3,
    sector_name: item.sector_name,
  };
}

export function CompareSelector({
  pathname,
  selectedCompanies,
  quickCompanies,
  availableYears,
  selectedYears,
  maxCompanies = DEFAULT_MAX_COMPANIES,
}: CompareSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<CompareCompanyOption[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [suggestionError, setSuggestionError] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);

  const selectedIds = useMemo(
    () => selectedCompanies.map((company) => company.cd_cvm),
    [selectedCompanies],
  );
  const selectedIdSet = useMemo(
    () => new Set(selectedIds),
    [selectedIds],
  );

  useEffect(() => {
    const normalized = deferredQuery.trim();

    if (normalized.length < 2 || selectedCompanies.length >= maxCompanies) {
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
          { cache: "no-store" },
        );
        const payload = (await response.json()) as SuggestionResponse;

        if (!active) {
          return;
        }

        if (!response.ok) {
          setSuggestions([]);
          setSuggestionError(payload.error ?? "Nao foi possivel buscar sugestoes.");
          return;
        }

        const nextSuggestions = (payload.items ?? [])
          .map(toCompareOption)
          .filter((item) => !selectedIdSet.has(item.cd_cvm));

        setSuggestions(nextSuggestions);
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
  }, [deferredQuery, maxCompanies, selectedCompanies.length, selectedIdSet]);

  function pushSelection(nextIds: number[], nextYears: number[] | null) {
    const queryString = mergeSearchParams(searchParams.toString(), {
      ids: nextIds.length > 0 ? serializeCompanyIds(nextIds) : null,
      anos:
        nextYears === null
          ? null
          : nextYears.length > 0
            ? serializeYears(nextYears)
            : null,
    });

    const href = queryString ? `${pathname}?${queryString}` : pathname;

    startTransition(() => {
      router.push(href);
    });
  }

  function addCompany(company: CompareCompanyOption) {
    if (selectedIdSet.has(company.cd_cvm)) {
      return;
    }

    if (selectedIds.length >= maxCompanies) {
      setSuggestionError(`Limite de ${maxCompanies} empresas nesta fase.`);
      return;
    }

    const nextIds = [...selectedIds, company.cd_cvm];

    track("compare_company_selected", {
      cd_cvm: company.cd_cvm,
      company_name: company.company_name,
      selected_count: nextIds.length,
    });

    setQuery("");
    setSuggestions([]);
    setSuggestionError(null);
    pushSelection(nextIds, null);
  }

  function removeCompany(cdCvm: number) {
    const nextIds = selectedIds.filter((id) => id !== cdCvm);

    track("compare_company_removed", {
      cd_cvm: cdCvm,
      selected_count: nextIds.length,
    });

    pushSelection(nextIds, null);
  }

  function toggleYear(year: number) {
    const currentYears = new Set(selectedYears);

    if (currentYears.has(year)) {
      if (currentYears.size === 1) {
        return;
      }
      currentYears.delete(year);
    } else {
      currentYears.add(year);
    }

    const nextYears = Array.from(currentYears).sort((left, right) => left - right);

    track("compare_years_changed", {
      years: nextYears.join(","),
      selected_companies: selectedIds.length,
    });

    pushSelection(selectedIds, nextYears);
  }

  function adjustComparison() {
    track("compare_adjust_clicked", {
      selected_companies: selectedIds.length,
      years: selectedYears.join(","),
    });

    pushSelection(selectedIds, selectedYears);
  }

  const quickOptions = quickCompanies.filter(
    (company) => !selectedIdSet.has(company.cd_cvm),
  );

  return (
    <SurfaceCard tone="subtle" padding="md" className="space-y-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
            Selecao da comparacao
          </p>
          <p className="text-sm leading-7 text-muted-foreground">
            Escolha entre 2 e {maxCompanies} empresas para comparar os indicadores no mesmo periodo.
          </p>
        </div>
        <InfoChip tone="muted">
          {selectedIds.length}/{maxCompanies} empresas
        </InfoChip>
      </div>

      <div className="space-y-3">
        <div className="flex flex-col gap-2">
          <div className="flex flex-1 items-center gap-3 rounded-[1.15rem] border border-border/65 bg-muted/55 px-4 py-3">
            <SearchIcon className="size-4 text-muted-foreground" />
            <Input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar empresa para adicionar"
              className="h-auto border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
              aria-label="Buscar empresa para comparar"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Digite ao menos 2 caracteres para receber sugestoes e adicionar empresas.
          </p>
        </div>

        {loadingSuggestions ? (
          <p className="text-sm text-muted-foreground">Buscando sugestoes...</p>
        ) : null}

        {suggestionError ? (
          <Alert className="rounded-2xl border border-destructive/20 bg-destructive/6 px-4 py-3">
            <AlertTitle>Busca de empresa indisponivel</AlertTitle>
            <AlertDescription>{suggestionError}</AlertDescription>
          </Alert>
        ) : null}

        {suggestions.length > 0 ? (
          <div className="grid gap-2 sm:grid-cols-2">
            {suggestions.map((item) => (
              <button
                key={item.cd_cvm}
                type="button"
                data-testid="compare-suggestion-add"
                className="flex items-center justify-between rounded-[1rem] border border-border/65 bg-background/90 px-4 py-3 text-left transition-colors hover:bg-muted/45"
                onClick={() => addCompany(item)}
              >
                <span className="space-y-1">
                  <span className="block text-sm font-medium text-foreground">{item.company_name}</span>
                  <span className="block text-xs text-muted-foreground">
                    {item.ticker_b3 ?? "Sem ticker"} - CVM {item.cd_cvm}
                  </span>
                </span>
                <PlusIcon className="size-4 text-muted-foreground" />
              </button>
            ))}
          </div>
        ) : null}

        {quickOptions.length > 0 && selectedIds.length < maxCompanies ? (
          <div className="space-y-2">
            <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Sugestoes rapidas</p>
            <div className="flex flex-wrap gap-2">
              {quickOptions.slice(0, 6).map((company) => (
                <button
                  key={company.cd_cvm}
                  type="button"
                  data-testid="compare-quick-add"
                  className={cn(
                    buttonVariants({ variant: "outline", size: "sm" }),
                    "rounded-full px-3",
                  )}
                  onClick={() => addCompany(company)}
                >
                  {company.company_name}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Empresas selecionadas</p>
        {selectedCompanies.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma empresa selecionada ainda.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selectedCompanies.map((company) => (
              <div
                key={company.cd_cvm}
                data-testid="compare-selected-chip"
                className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/88 px-3 py-1.5 text-sm"
              >
                <Link
                  href={`/empresas/${company.cd_cvm}`}
                  className="font-medium text-foreground hover:underline"
                >
                  {company.company_name}
                </Link>
                <span className="text-xs text-muted-foreground">{company.ticker_b3 ?? "-"}</span>
                <button
                  type="button"
                  onClick={() => removeCompany(company.cd_cvm)}
                  className="inline-flex size-5 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label={`Remover ${company.company_name}`}
                >
                  <XIcon className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="space-y-3">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">Periodo em comum</p>
        {availableYears.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            As empresas atuais nao possuem anos em comum para comparacao.
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {availableYears.map((year) => {
                const active = selectedYears.includes(year);
                return (
                  <Button
                    key={year}
                    type="button"
                    variant={active ? "secondary" : "outline"}
                    size="sm"
                    className="rounded-full px-4"
                    onClick={() => toggleYear(year)}
                  >
                    {year}
                  </Button>
                );
              })}
            </div>
            <p className="text-xs text-muted-foreground">
              Janela selecionada: {formatYearsLabel(selectedYears)}
            </p>
          </>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <ExcelDownloadButton
          endpoint={`/api/compare/excel?ids=${encodeURIComponent(serializeCompanyIds(selectedIds))}`}
          fallbackFilename="comparar_excel_lote.zip"
          buttonLabel="Baixar lote Excel"
          pendingLabel="Preparando lote..."
          trackingEvent="compare_excel_download_clicked"
          failureTrackingEvent="compare_excel_download_failed"
          trackingPayload={{
            selected_companies: selectedIds.length,
            years: selectedYears.join(","),
          }}
          disabled={selectedIds.length < 2}
          className="rounded-full px-5"
        />
        <Button
          type="button"
          size="lg"
          className="rounded-full px-5"
          onClick={adjustComparison}
          disabled={selectedIds.length < 2 || selectedYears.length === 0}
        >
          Ajustar comparacao
        </Button>
        <button
          type="button"
          className={cn(buttonVariants({ variant: "outline", size: "lg" }), "rounded-full px-5")}
          onClick={() => {
            track("compare_reset_clicked", {
              selected_companies: selectedIds.length,
            });
            startTransition(() => {
              router.push(pathname);
            });
          }}
        >
          Limpar selecao
        </button>
      </div>
    </SurfaceCard>
  );
}
