"use client";

import { startTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { mergeSearchParams } from "@/lib/search-params";
import { track } from "@/lib/track";

type DirectoryPaginationProps = {
  currentPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  currentSearch: string;
  currentSector: string | null;
};

function getVisiblePages(currentPage: number, totalPages: number): number[] {
  const pages = new Set([1, totalPages, currentPage - 1, currentPage, currentPage + 1]);

  return Array.from(pages)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((left, right) => left - right);
}

export function DirectoryPagination({
  currentPage,
  totalPages,
  hasNext,
  hasPrevious,
  currentSearch,
  currentSector,
}: DirectoryPaginationProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  if (totalPages <= 1) {
    return null;
  }

  function goTo(page: number) {
    const query = mergeSearchParams(searchParams.toString(), {
      busca: currentSearch || null,
      setor: currentSector,
      pagina: page === 1 ? null : page,
    });

    track("companies_pagination_clicked", {
      page,
      search: currentSearch,
      sector: currentSector,
    });

    startTransition(() => {
      router.push(query ? `/empresas?${query}` : "/empresas");
    });
  }

  const visiblePages = getVisiblePages(currentPage, totalPages);

  return (
    <Pagination className="justify-start">
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious
            href="#"
            text="Anterior"
            aria-disabled={!hasPrevious}
            className={!hasPrevious ? "pointer-events-none opacity-40" : ""}
            onClick={(event) => {
              event.preventDefault();
              if (hasPrevious) {
                goTo(currentPage - 1);
              }
            }}
          />
        </PaginationItem>

        {visiblePages.map((page, index) => {
          const previous = visiblePages[index - 1];
          const showEllipsis = previous && page - previous > 1;

          return (
            <PaginationItem key={page}>
              {showEllipsis ? <PaginationEllipsis /> : null}
              <PaginationLink
                href="#"
                isActive={page === currentPage}
                onClick={(event) => {
                  event.preventDefault();
                  goTo(page);
                }}
              >
                {page}
              </PaginationLink>
            </PaginationItem>
          );
        })}

        <PaginationItem>
          <PaginationNext
            href="#"
            text="Proxima"
            aria-disabled={!hasNext}
            className={!hasNext ? "pointer-events-none opacity-40" : ""}
            onClick={(event) => {
              event.preventDefault();
              if (hasNext) {
                goTo(currentPage + 1);
              }
            }}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  );
}
