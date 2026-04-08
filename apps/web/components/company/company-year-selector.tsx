"use client";

import { startTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { mergeSearchParams, serializeYears } from "@/lib/search-params";
import { track } from "@/lib/track";

type CompanyYearSelectorProps = {
  pathname: string;
  availableYears: number[];
  selectedYears: number[];
};

export function CompanyYearSelector({
  pathname,
  availableYears,
  selectedYears,
}: CompanyYearSelectorProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

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
    const query = mergeSearchParams(searchParams.toString(), {
      anos: serializeYears(nextYears),
    });

    track("company_years_changed", {
      years: nextYears.join(","),
    });

    startTransition(() => {
      router.push(`${pathname}?${query}`);
    });
  }

  return (
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
  );
}
