"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { track } from "@/lib/track";

type SectorCompanyLinkProps = {
  href: string;
  sectorSlug: string;
  selectedYear: number;
  cdCvm: number;
  companyName: string;
  children: ReactNode;
  className?: string;
};

export function SectorCompanyLink({
  href,
  sectorSlug,
  selectedYear,
  cdCvm,
  companyName,
  children,
  className,
}: SectorCompanyLinkProps) {
  return (
    <Link
      href={href}
      className={className}
      onClick={() => {
        track("sector_company_clicked", {
          sector_slug: sectorSlug,
          selected_year: selectedYear,
          cd_cvm: cdCvm,
          company_name: companyName,
        });
      }}
    >
      {children}
    </Link>
  );
}
