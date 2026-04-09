"use client";

import { useEffect } from "react";

import { track } from "@/lib/track";

type SectorHubTrackerProps = {
  sectorCount: number;
};

export function SectorHubTracker({ sectorCount }: SectorHubTrackerProps) {
  useEffect(() => {
    track("sectors_hub_viewed", {
      sector_count: sectorCount,
    });
  }, [sectorCount]);

  return null;
}
