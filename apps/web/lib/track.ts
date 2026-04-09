export type TrackEventName =
  | "home_search_submitted"
  | "home_suggestion_selected"
  | "companies_filter_changed"
  | "companies_pagination_clicked"
  | "company_detail_viewed"
  | "company_excel_download_clicked"
  | "company_excel_download_failed"
  | "company_years_changed"
  | "company_statement_changed"
  | "compare_viewed"
  | "compare_company_selected"
  | "compare_excel_download_clicked"
  | "compare_excel_download_failed"
  | "compare_company_removed"
  | "compare_years_changed"
  | "compare_adjust_clicked"
  | "compare_reset_clicked"
  | "sectors_hub_viewed"
  | "sector_detail_viewed"
  | "sector_year_changed"
  | "sector_company_clicked";

type TrackPayload = Record<string, string | number | boolean | null | undefined>;

declare global {
  interface Window {
    __CVM_ANALYTICS_EVENTS__?: Array<{
      event: TrackEventName;
      payload: TrackPayload;
      timestamp: string;
    }>;
  }
}

export function track(event: TrackEventName, payload: TrackPayload = {}): void {
  if (typeof window === "undefined") {
    return;
  }

  const entry = {
    event,
    payload,
    timestamp: new Date().toISOString(),
  };

  window.__CVM_ANALYTICS_EVENTS__ ??= [];
  window.__CVM_ANALYTICS_EVENTS__.push(entry);

  if (process.env.NODE_ENV !== "production") {
    console.info("[track]", entry);
  }
}
