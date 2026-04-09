"use client";

import { useEffect } from "react";

import { track } from "@/lib/track";

type CompareTrackerProps = {
  companyIds: number[];
  years: number[];
  comparableCompanies: number;
};

export function CompareTracker({
  companyIds,
  years,
  comparableCompanies,
}: CompareTrackerProps) {
  useEffect(() => {
    track("compare_viewed", {
      companies_selected: companyIds.length,
      companies_comparable: comparableCompanies,
      ids: companyIds.join(","),
      years: years.join(","),
    });
  }, [companyIds, comparableCompanies, years]);

  return null;
}
