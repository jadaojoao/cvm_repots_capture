"use client";

import { startTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { mergeSearchParams } from "@/lib/search-params";
import { track } from "@/lib/track";

type SectorYearSelectorProps = {
  pathname: string;
  sectorSlug: string;
  availableYears: number[];
  selectedYear: number;
};

export function SectorYearSelector({
  pathname,
  sectorSlug,
  availableYears,
  selectedYear,
}: SectorYearSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const yearOptions = [...availableYears].sort((left, right) => right - left);

  function selectYear(year: number) {
    const query = mergeSearchParams(searchParams.toString(), {
      ano: year,
    });

    track("sector_year_changed", {
      sector_slug: sectorSlug,
      year,
    });

    startTransition(() => {
      router.push(`${pathname}?${query}`);
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {yearOptions.map((year) => {
        const active = year === selectedYear;

        return (
          <Button
            key={year}
            type="button"
            variant={active ? "secondary" : "outline"}
            size="sm"
            className="rounded-full px-4"
            onClick={() => selectYear(year)}
          >
            {year}
          </Button>
        );
      })}
    </div>
  );
}
