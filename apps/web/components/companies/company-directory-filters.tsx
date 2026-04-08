"use client";

import { SearchIcon } from "lucide-react";
import { startTransition, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { SurfaceCard } from "@/components/shared/design-system-recipes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CompanySectorFilter } from "@/lib/api";
import { mergeSearchParams } from "@/lib/search-params";
import { track } from "@/lib/track";

type CompanyDirectoryFiltersProps = {
  currentSearch: string;
  currentSector: string | null;
  sectors: CompanySectorFilter[];
  sectorFilterUnavailable?: boolean;
};

export function CompanyDirectoryFilters({
  currentSearch,
  currentSector,
  sectors,
  sectorFilterUnavailable = false,
}: CompanyDirectoryFiltersProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(currentSearch);
  const hasCurrentSector = sectors.some(
    (sector) => sector.sector_slug === currentSector,
  );
  const selectValue =
    sectorFilterUnavailable || !hasCurrentSector
      ? "all"
      : currentSector ?? "all";

  function pushFilters(updates: Record<string, string | number | null | undefined>) {
    const query = mergeSearchParams(searchParams.toString(), updates);
    const href = query ? `/empresas?${query}` : "/empresas";

    startTransition(() => {
      router.push(href);
    });
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    track("companies_filter_changed", {
      search,
      sector: currentSector,
      source: "search",
    });

    pushFilters({
      busca: search.trim() || null,
      setor:
        sectorFilterUnavailable || (currentSector !== null && !hasCurrentSector)
          ? null
          : undefined,
      pagina: null,
    });
  }

  return (
    <SurfaceCard tone="subtle" padding="md">
      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-3 lg:flex-row lg:items-center"
      >
        <div className="flex flex-1 items-center gap-3 rounded-[1.15rem] border border-border/65 bg-muted/55 px-4 py-3">
          <SearchIcon className="size-4 text-muted-foreground" />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por nome, ticker ou codigo CVM"
            className="h-auto border-0 bg-transparent p-0 shadow-none focus-visible:ring-0"
          />
        </div>

        <div className="flex flex-col gap-3 sm:flex-row lg:w-auto">
          <Select
            value={selectValue}
            disabled={sectorFilterUnavailable}
            onValueChange={(value) => {
              const nextSector = value === "all" ? null : value;
              track("companies_filter_changed", {
                search,
                sector: nextSector,
                source: "sector",
              });
              pushFilters({
                setor: nextSector,
                pagina: null,
              });
            }}
          >
            <SelectTrigger className="h-11 min-w-56 rounded-[1.15rem] bg-background px-4">
              <SelectValue
                placeholder={
                  sectorFilterUnavailable
                    ? "Filtro setorial indisponivel"
                    : "Todos os setores"
                }
              />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">Todos os setores</SelectItem>
                {!sectorFilterUnavailable
                  ? sectors.map((sector) => (
                      <SelectItem key={sector.sector_slug} value={sector.sector_slug}>
                        {sector.sector_name} - {sector.company_count}
                      </SelectItem>
                    ))
                  : null}
              </SelectGroup>
            </SelectContent>
          </Select>

          <Button type="submit" size="lg" className="h-11 rounded-full px-5">
            Aplicar filtros
          </Button>
        </div>
      </form>
    </SurfaceCard>
  );
}
