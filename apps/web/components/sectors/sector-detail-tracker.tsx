"use client";

import { useEffect } from "react";

import { track } from "@/lib/track";

type SectorDetailTrackerProps = {
  sectorSlug: string;
  sectorName: string;
  selectedYear: number;
  companyCount: number;
};

export function SectorDetailTracker({
  sectorSlug,
  sectorName,
  selectedYear,
  companyCount,
}: SectorDetailTrackerProps) {
  useEffect(() => {
    track("sector_detail_viewed", {
      sector_slug: sectorSlug,
      sector_name: sectorName,
      selected_year: selectedYear,
      company_count: companyCount,
    });
  }, [companyCount, sectorName, sectorSlug, selectedYear]);

  return null;
}
