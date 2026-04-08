import {
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import type { StatementMatrix, TabularDataRow } from "@/lib/api";
import { isStatementSubtotal } from "@/lib/constants";
import { formatStatementValue } from "@/lib/formatters";
import { cn } from "@/lib/utils";

type CompanyStatementsProps = {
  matrix: StatementMatrix;
};

export function CompanyStatements({ matrix }: CompanyStatementsProps) {
  const periodColumns = matrix.table.columns.filter(
    (column) =>
      !["CD_CONTA", "DS_CONTA", "STANDARD_NAME", "LINE_ID_BASE"].includes(column),
  );
  const rows = matrix.table.rows as TabularDataRow[];

  if (rows.length === 0) {
    return (
      <SurfaceCard tone="muted" padding="hero" className="items-center text-center">
        <p className="font-heading text-2xl text-foreground">
          Sem demonstracao disponivel.
        </p>
        <p className="max-w-2xl text-sm leading-7 text-muted-foreground">
          Ajuste o periodo selecionado ou troque o tipo de demonstracao para
          consultar outra visao disponivel.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard tone="default" padding="none" className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-muted/35">
            <tr className="[&_th]:border-b [&_th]:border-border/60">
              <th className="sticky left-0 z-10 bg-muted/35 px-5 py-3 text-left font-medium text-foreground">
                Conta
              </th>
              {periodColumns.map((column) => (
                <th
                  key={column}
                  className="px-5 py-3 text-right font-medium text-foreground"
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const accountCode = String(row.CD_CONTA ?? "");
              const isSubtotal = isStatementSubtotal(
                matrix.statement_type,
                accountCode,
              );

              return (
                <tr
                  key={String(row.LINE_ID_BASE ?? accountCode)}
                  className={cn(
                    "border-b border-border/45",
                    isSubtotal ? "bg-muted/35" : "hover:bg-muted/20",
                  )}
                >
                  <td className="sticky left-0 z-10 min-w-84 bg-inherit px-5 py-3 align-top">
                    <div className="space-y-1">
                      <p
                        className={cn(
                          "font-medium text-foreground",
                          isSubtotal ? "font-semibold" : "",
                        )}
                      >
                        {accountCode} - {String(row.DS_CONTA ?? "Conta")}
                      </p>
                      <p className="text-xs uppercase tracking-[0.12em] text-muted-foreground">
                        {String(row.STANDARD_NAME ?? row.DS_CONTA ?? "")}
                      </p>
                    </div>
                  </td>
                  {periodColumns.map((column) => {
                    const rawValue = row[column];
                    const numericValue =
                      rawValue === null || rawValue === undefined
                        ? null
                        : Number(rawValue);

                    return (
                      <td
                        key={`${row.LINE_ID_BASE}-${column}`}
                        className={cn(
                          "px-5 py-3 text-right text-foreground/90",
                          numericValue !== null && numericValue < 0
                            ? "text-destructive"
                            : "",
                          isSubtotal ? "font-semibold" : "",
                        )}
                      >
                        {formatStatementValue(numericValue)}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </SurfaceCard>
  );
}
