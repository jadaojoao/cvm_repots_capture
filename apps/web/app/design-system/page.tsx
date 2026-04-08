"use client";

import dynamic from "next/dynamic";
import type { ReactNode } from "react";
import { Home, Search, BarChart2, Bookmark, User } from "lucide-react";

import { Calendar } from "@/components/calendar";
import { Accordion, AccordionItem, AccordionPanel, AccordionTrigger } from "@/components/coss-accordion";
import ContentTooltipDemo from "@/components/contemt-tooltip";
import { NativeDelete } from "@/components/delete-button";
import { InteractiveMenu } from "@/components/modern-mobile-menu";
import {
  InfoChip,
  SectionHeading,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import SwitchToggleThemeDemo from "@/components/toggle-theme";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { CheckboxGroup } from "@/components/ui/checkbox-group";
import { Field, FieldError, FieldItem, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import InteractiveHoverButton from "@/components/ui/interactive-hover-button";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Toolbar, ToolbarButton, ToolbarGroup } from "@/components/ui/toolbar";
import AnimatedDropdown from "@/components/ui/animated-dropdown";
import { cn } from "@/lib/utils";
import SwitchWithDescriptionDemo from "@/components/with-description";

const FeatureCarousel = dynamic(() => import("@/components/feature-carousel"), {
  ssr: false,
  loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" />,
});

const FinancialTable = dynamic(
  () =>
    import("@/components/financial-markets-table").then((module) => ({
      default: module.FinancialTable,
    })),
  {
    ssr: false,
    loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" />,
  },
);

const LeadsTable = dynamic(
  () =>
    import("@/components/leads-data-table").then((module) => ({
      default: module.LeadsTable,
    })),
  {
    ssr: false,
    loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" />,
  },
);

const ServerManagementTable = dynamic(
  () =>
    import("@/components/server-management-table").then((module) => ({
      default: module.ServerManagementTable,
    })),
  {
    ssr: false,
    loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" />,
  },
);

const IncidentSummaryCard = dynamic(
  () => import("@/components/horizontal-bar-chart"),
  {
    ssr: false,
    loading: () => <div className="h-64 animate-pulse rounded-xl bg-muted" />,
  },
);

const AdvancedIncidentReportCard = dynamic(
  () => import("@/components/area-chart-medium"),
  {
    ssr: false,
    loading: () => <div className="h-64 animate-pulse rounded-xl bg-muted" />,
  },
);

const NAV = [
  {
    group: "Foundation",
    items: [
      { label: "UI Colors", href: "#colors" },
      { label: "Chart Palette", href: "#chart-colors" },
      { label: "Spacing", href: "#spacing" },
      { label: "Typography", href: "#typography" },
      { label: "Border Radius", href: "#radius" },
    ],
  },
  {
    group: "Data Viz",
    items: [
      { label: "Charts", href: "#charts" },
      { label: "Tables", href: "#tables" },
    ],
  },
  {
    group: "Navigation",
    items: [
      { label: "Tabs", href: "#tabs" },
      { label: "Toolbar", href: "#toolbar" },
      { label: "Dropdown", href: "#dropdown" },
      { label: "Mobile Menu", href: "#mobile-menu" },
    ],
  },
  {
    group: "Forms",
    items: [
      { label: "Field", href: "#field" },
      { label: "Inputs", href: "#inputs" },
      { label: "Textarea", href: "#textarea" },
      { label: "Checkbox", href: "#checkbox" },
      { label: "Calendar", href: "#calendar" },
    ],
  },
  {
    group: "Feedback",
    items: [
      { label: "Accordion", href: "#accordion" },
      { label: "Tooltip", href: "#tooltip" },
    ],
  },
  {
    group: "Actions",
    items: [
      { label: "Buttons", href: "#buttons" },
      { label: "Icons", href: "#icons" },
      { label: "Delete Button", href: "#delete-button" },
    ],
  },
  {
    group: "Utilities",
    items: [
      { label: "Toggle Theme", href: "#toggle-theme" },
      { label: "Switch", href: "#switch" },
    ],
  },
  {
    group: "Marketing",
    items: [{ label: "Feature Carousel", href: "#carousel" }],
  },
] as const;

const SUMMARY_CARDS = [
  {
    label: "Foundation",
    value: "Tokens and typography",
    note: "Colors, spacing, radius, iconography, and modes",
  },
  {
    label: "Recipes",
    value: "Shared product surfaces",
    note: "Page shell, elevated card, chips, headings, and tables",
  },
  {
    label: "Scope",
    value: "Home, directory, company detail",
    note: "Aligned to the current public V2 routes only",
  },
] as const;

const UI_COLORS = [
  { name: "Background", cls: "border border-border bg-background" },
  { name: "Foreground", cls: "bg-foreground" },
  { name: "Primary", cls: "bg-primary" },
  { name: "Secondary", cls: "border border-border/40 bg-secondary" },
  { name: "Muted", cls: "border border-border/40 bg-muted" },
  { name: "Accent", cls: "border border-border/40 bg-accent" },
  { name: "Destructive", cls: "bg-destructive" },
  { name: "Border", cls: "border-4 border-border bg-background" },
] as const;

const CHART_COLORS = [
  { name: "Chart 1 - Teal", token: "--chart-1", hue: "161 deg", note: "Primary / brand" },
  { name: "Chart 2 - Amber", token: "--chart-2", hue: "29 deg", note: "Complementary contrast" },
  { name: "Chart 3 - Blue Violet", token: "--chart-3", hue: "258 deg", note: "" },
  { name: "Chart 4 - Lime", token: "--chart-4", hue: "79 deg", note: "" },
  { name: "Chart 5 - Rose", token: "--chart-5", hue: "320 deg", note: "" },
] as const;

const SPACING_SCALE = [
  { token: "space-1", px: 4 },
  { token: "space-2", px: 8 },
  { token: "space-4", px: 16 },
  { token: "space-8", px: 32 },
  { token: "space-12", px: 48 },
  { token: "space-16", px: 64 },
  { token: "space-20", px: 80 },
  { token: "space-24", px: 96 },
] as const;

const RADIUS_SCALE = [
  { label: "none", cls: "rounded-none" },
  { label: "sm", cls: "rounded-sm" },
  {
    label: "md",
    cls: "rounded-md ring-2 ring-primary/50 ring-offset-2 ring-offset-card",
  },
  { label: "lg", cls: "rounded-lg" },
  { label: "xl", cls: "rounded-xl" },
  { label: "2xl", cls: "rounded-2xl" },
  { label: "full", cls: "rounded-full" },
] as const;

const ICON_NAMES = [
  "search",
  "home",
  "analytics",
  "trending_up",
  "business_center",
  "account_circle",
  "settings",
  "notifications",
  "bookmark",
  "share",
  "download",
  "filter_list",
  "close",
  "check_circle",
  "arrow_forward",
  "expand_more",
  "compare",
  "table_chart",
  "bar_chart",
  "show_chart",
] as const;

function Icon({
  name,
  size = 24,
  className,
}: {
  name: string;
  size?: number;
  className?: string;
}) {
  return (
    <span
      className={cn("material-symbols-outlined select-none leading-none", className)}
      style={{ fontSize: size, fontVariationSettings: "'wght' 200" }}
    >
      {name}
    </span>
  );
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 space-y-5">
      <div className="border-b border-border pb-3">
        <h2 className="font-heading text-2xl font-semibold tracking-tight">
          {title}
        </h2>
      </div>
      <SurfaceCard tone="subtle" padding="lg" className="rounded-[1.5rem]">
        {children}
      </SurfaceCard>
    </section>
  );
}

export default function DesignSystemPage() {
  return (
    <>
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,200,0,0"
      />

      <div className="flex min-h-screen">
        <aside className="hidden w-52 shrink-0 border-r border-border/60 lg:block">
          <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto px-4 py-8">
            <div className="mb-6 flex items-center gap-2">
              <div className="h-4 w-4 rounded-sm bg-primary" />
              <span className="font-mono text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Design System
              </span>
            </div>
            <nav className="space-y-5">
              {NAV.map((group) => (
                <div key={group.group}>
                  <p className="mb-1.5 text-[0.65rem] font-semibold uppercase tracking-[0.16em] text-muted-foreground/70">
                    {group.group}
                  </p>
                  <ul className="space-y-0.5">
                    {group.items.map((item) => (
                      <li key={item.href}>
                        <a
                          href={item.href}
                          className="block rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                        >
                          {item.label}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </nav>
          </div>
        </aside>

        <main className="flex-1 px-6 py-12 lg:px-16 xl:px-20">
          <div className="mx-auto max-w-4xl space-y-24">
            <SurfaceCard tone="hero" padding="hero" className="space-y-8">
              <SectionHeading
                eyebrow="Internal tooling"
                title="Design System"
                description="Catalog of tokens, shared primitives, and visual recipes that define the V2 web slice. This route documents the product system and should not evolve as a second product surface."
                titleAs="h1"
                meta={
                  <>
                    <InfoChip tone="brand">Reference</InfoChip>
                    <InfoChip tone="muted">Conservative migration</InfoChip>
                  </>
                }
              />
              <div className="grid gap-4 sm:grid-cols-3">
                {SUMMARY_CARDS.map((item) => (
                  <div
                    key={item.label}
                    className="rounded-[1.25rem] border border-border/65 bg-background/72 p-4"
                  >
                    <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">
                      {item.label}
                    </p>
                    <p className="mt-3 text-base font-semibold text-foreground">
                      {item.value}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">
                      {item.note}
                    </p>
                  </div>
                ))}
              </div>
            </SurfaceCard>

            <Section id="colors" title="UI Colors">
              <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
                {UI_COLORS.map((color) => (
                  <div key={color.name} className="space-y-2">
                    <div className={cn("h-20 w-full rounded-md", color.cls)} />
                    <p className="text-sm font-medium">{color.name}</p>
                  </div>
                ))}
              </div>
            </Section>

            <Section id="chart-colors" title="Chart Palette">
              <p className="mb-5 text-sm text-muted-foreground">
                Hues are spaced by roughly 72 deg on the OkLch circle, with real chroma in both light and dark mode.
              </p>
              <div className="space-y-4">
                {CHART_COLORS.map((color) => (
                  <div key={color.token} className="flex items-center gap-4">
                    <div
                      className="h-8 w-8 shrink-0 rounded-md"
                      style={{ backgroundColor: `var(${color.token})` }}
                    />
                    <div className="w-52">
                      <p className="text-sm font-medium">{color.name}</p>
                      <p className="font-mono text-xs text-muted-foreground">
                        {color.token} - {color.hue}
                      </p>
                    </div>
                    <div
                      className="h-2 flex-1 rounded-full opacity-80"
                      style={{ backgroundColor: `var(${color.token})` }}
                    />
                    {color.note ? (
                      <span className="text-xs text-muted-foreground">
                        {color.note}
                      </span>
                    ) : null}
                  </div>
                ))}
              </div>
            </Section>

            <Section id="spacing" title="Spacing">
              <div className="space-y-3">
                {SPACING_SCALE.map((item) => (
                  <div key={item.token} className="flex items-center gap-4">
                    <span className="w-28 shrink-0 font-mono text-xs text-muted-foreground">
                      {item.token} - {item.px}px
                    </span>
                    <div
                      className="h-5 rounded-sm bg-primary/25"
                      style={{ width: item.px }}
                    />
                  </div>
                ))}
              </div>
            </Section>

            <Section id="typography" title="Typography">
              <div className="space-y-10">
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">
                    Space Grotesk - heading
                  </p>
                  <p className="font-heading text-5xl font-bold tracking-tight">
                    The quick brown fox
                  </p>
                  <p className="font-heading text-3xl font-semibold">
                    jumps over the lazy dog
                  </p>
                  <p className="font-heading text-xl font-medium">
                    0123456789 AaBbCcDd
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">
                    Manrope - body
                  </p>
                  <p className="text-base leading-relaxed text-foreground">
                    Public financial analysis platform for CVM filings, focused
                    on fast discovery, historical reading, and navigation
                    across 449+ listed companies.
                  </p>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Secondary text, explanations, and interface metadata.
                  </p>
                  <p className="text-xs text-muted-foreground/70">
                    Tertiary text, labels, and table headers.
                  </p>
                </div>
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">
                    IBM Plex Mono - mono
                  </p>
                  <code className="font-mono text-sm">
                    import {"{"} CVMQueryLayer {"}"} from &quot;@/src/query_layer&quot;
                  </code>
                  <p className="font-mono text-xs text-muted-foreground">
                    LINE_ID_BASE - CD_CONTA - PERIODO_LABEL
                  </p>
                </div>
              </div>
            </Section>

            <Section id="radius" title="Border Radius">
              <div className="flex flex-wrap gap-6">
                {RADIUS_SCALE.map((radius) => (
                  <div key={radius.label} className="flex flex-col items-center gap-2">
                    <div
                      className={cn(
                        "h-14 w-14 border-2 border-primary/40 bg-primary/10",
                        radius.cls,
                      )}
                    />
                    <span className="font-mono text-xs text-muted-foreground">
                      {radius.label}
                      {radius.label === "md" ? " <- base" : ""}
                    </span>
                  </div>
                ))}
              </div>
            </Section>

            <Section id="charts" title="Charts - reaviz">
              <div className="space-y-10">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Horizontal bar chart
                  </p>
                  <IncidentSummaryCard />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Area chart, multi series
                  </p>
                  <AdvancedIncidentReportCard />
                </div>
              </div>
            </Section>

            <Section id="tables" title="Tables">
              <div className="space-y-12">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Financial markets table
                  </p>
                  <FinancialTable />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Leads data table
                  </p>
                  <LeadsTable />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Server management table
                  </p>
                  <ServerManagementTable />
                </div>
              </div>
            </Section>

            <Section id="tabs" title="Tabs - coss.com">
              <Tabs defaultValue="overview">
                <TabsList variant="underline">
                  <TabsTab value="overview">Overview</TabsTab>
                  <TabsTab value="analytics">Analysis</TabsTab>
                  <TabsTab value="reports">Reports</TabsTab>
                  <TabsTab value="settings" disabled>
                    Settings
                  </TabsTab>
                </TabsList>
                <TabsPanel value="overview" className="mt-4 text-sm text-muted-foreground">
                  Overview tab content for KPIs, summaries, and first-pass company reading.
                </TabsPanel>
                <TabsPanel value="analytics" className="mt-4 text-sm text-muted-foreground">
                  Analysis tab content for comparisons, charts, and trend reading.
                </TabsPanel>
                <TabsPanel value="reports" className="mt-4 text-sm text-muted-foreground">
                  Reports tab content for statements, exports, and raw financial data.
                </TabsPanel>
              </Tabs>
            </Section>

            <Section id="toolbar" title="Toolbar - coss.com">
              <Toolbar>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Bold">
                    <Icon name="format_bold" size={18} />
                  </ToolbarButton>
                  <ToolbarButton aria-label="Italic">
                    <Icon name="format_italic" size={18} />
                  </ToolbarButton>
                  <ToolbarButton aria-label="Underline">
                    <Icon name="format_underlined" size={18} />
                  </ToolbarButton>
                </ToolbarGroup>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Align left">
                    <Icon name="format_align_left" size={18} />
                  </ToolbarButton>
                  <ToolbarButton aria-label="Align center">
                    <Icon name="format_align_center" size={18} />
                  </ToolbarButton>
                  <ToolbarButton aria-label="Align right">
                    <Icon name="format_align_right" size={18} />
                  </ToolbarButton>
                </ToolbarGroup>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Filter">
                    <Icon name="filter_list" size={18} />
                  </ToolbarButton>
                  <ToolbarButton aria-label="Download">
                    <Icon name="download" size={18} />
                  </ToolbarButton>
                </ToolbarGroup>
              </Toolbar>
            </Section>

            <Section id="dropdown" title="Animated Dropdown - Shatlyk1011">
              <div className="flex flex-wrap gap-4">
                <AnimatedDropdown
                  text="Exportar"
                  items={[
                    { name: "Excel (.xlsx)", link: "#" },
                    { name: "CSV", link: "#" },
                    { name: "PDF", link: "#" },
                  ]}
                />
                <AnimatedDropdown
                  text="Acoes"
                  items={[
                    { name: "Comparar", link: "#" },
                    { name: "Compartilhar", link: "#" },
                    { name: "Configuracoes", link: "#" },
                  ]}
                />
              </div>
            </Section>

            <Section id="mobile-menu" title="Mobile Navigation - easemize">
              <div className="flex justify-center py-4">
                <InteractiveMenu
                  items={[
                    { icon: Home, label: "Home" },
                    { icon: Search, label: "Buscar" },
                    { icon: BarChart2, label: "KPIs" },
                    { icon: Bookmark, label: "Salvos" },
                    { icon: User, label: "Perfil" },
                  ]}
                />
              </div>
            </Section>

            <Section id="field" title="Field - coss.com">
              <div className="grid max-w-lg gap-5 sm:grid-cols-2">
                <Field>
                  <FieldLabel>Empresa</FieldLabel>
                  <FieldItem>
                    <Input placeholder="Ex: Petrobras" />
                  </FieldItem>
                </Field>
                <Field>
                  <FieldLabel>Ano fiscal</FieldLabel>
                  <FieldItem>
                    <Input placeholder="2024" />
                  </FieldItem>
                </Field>
                <Field>
                  <FieldLabel>Campo com erro</FieldLabel>
                  <FieldItem>
                    <Input aria-invalid placeholder="CNPJ invalido" />
                  </FieldItem>
                  <FieldError>CNPJ nao encontrado na CVM.</FieldError>
                </Field>
                <Field>
                  <FieldLabel>Desabilitado</FieldLabel>
                  <FieldItem>
                    <Input disabled placeholder="Indisponivel" />
                  </FieldItem>
                </Field>
              </div>
            </Section>

            <Section id="inputs" title="Inputs">
              <div className="flex max-w-sm flex-col gap-4">
                <Input placeholder="Default" />
                <div className="relative">
                  <Icon
                    name="search"
                    size={18}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
                  />
                  <Input placeholder="Search..." className="pl-9" />
                </div>
                <Input aria-invalid placeholder="Error state" />
                <Input disabled placeholder="Disabled" />
              </div>
            </Section>

            <Section id="textarea" title="Textarea - coss.com">
              <div className="flex max-w-sm flex-col gap-4">
                <Textarea
                  placeholder="Adicione uma observacao sobre a empresa..."
                  rows={4}
                />
                <Textarea placeholder="Desabilitado..." disabled rows={3} />
              </div>
            </Section>

            <Section id="checkbox" title="Checkbox Group - coss.com">
              <div className="flex flex-wrap gap-8">
                <div>
                  <p className="mb-3 text-sm font-medium">Demonstracoes</p>
                  <CheckboxGroup className="gap-3">
                    {["DRE", "BPA", "BPP", "DFC", "DVA"].map((item) => (
                      <div key={item} className="flex items-center gap-2">
                        <Checkbox id={`chk-${item}`} />
                        <Label htmlFor={`chk-${item}`} className="text-sm">
                          {item}
                        </Label>
                      </div>
                    ))}
                  </CheckboxGroup>
                </div>
              </div>
            </Section>

            <Section id="calendar" title="Calendar - coss.com">
              <Calendar />
            </Section>

            <Section id="accordion" title="Accordion - coss.com">
              <Accordion>
                <AccordionItem value="dfp">
                  <AccordionTrigger>O que e DFP?</AccordionTrigger>
                  <AccordionPanel>
                    Demonstracoes Financeiras Padronizadas, the annual filing
                    sent to the CVM by listed companies.
                  </AccordionPanel>
                </AccordionItem>
                <AccordionItem value="itr">
                  <AccordionTrigger>O que e ITR?</AccordionTrigger>
                  <AccordionPanel>
                    Informacoes Trimestrais, the quarterly filing with condensed
                    financial statements.
                  </AccordionPanel>
                </AccordionItem>
                <AccordionItem value="kpis">
                  <AccordionTrigger>Como os KPIs sao calculados?</AccordionTrigger>
                  <AccordionPanel>
                    Calculated in{" "}
                    <code className="rounded bg-muted px-1 font-mono text-xs">
                      kpi_engine.py
                    </code>{" "}
                    with 60+ indicators including ROE, ROA, margins, solvency,
                    and liquidity.
                  </AccordionPanel>
                </AccordionItem>
              </Accordion>
            </Section>

            <Section id="tooltip" title="Tooltip - larsen66">
              <ContentTooltipDemo />
            </Section>

            <Section id="buttons" title="Buttons">
              <div className="space-y-6">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Variants
                  </p>
                  <div className="flex flex-wrap gap-3">
                    <Button>Primary</Button>
                    <Button variant="secondary">Secondary</Button>
                    <Button variant="outline">Outline</Button>
                    <Button variant="ghost">Ghost</Button>
                    <Button variant="destructive">Destructive</Button>
                  </div>
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    Sizes
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <Button size="sm">Small</Button>
                    <Button>Medium</Button>
                    <Button size="lg">Large</Button>
                  </div>
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">
                    States and variants
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <Button disabled>Disabled</Button>
                    <Button variant="outline">
                      <Icon name="download" size={18} /> Download
                    </Button>
                    <InteractiveHoverButton text="Hover me" />
                  </div>
                </div>
              </div>
            </Section>

            <Section id="icons" title="Icons - Material Symbols Outlined, weight 200">
              <div className="space-y-6">
                <div className="flex flex-wrap items-end gap-5">
                  {[16, 20, 24, 32, 40].map((size) => (
                    <div key={size} className="flex flex-col items-center gap-2">
                      <div className="flex h-14 w-14 items-center justify-center rounded-md border border-border bg-muted">
                        <Icon name="analytics" size={size} />
                      </div>
                      <span className="font-mono text-xs text-muted-foreground">
                        {size}px
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {ICON_NAMES.map((icon) => (
                    <div
                      key={icon}
                      title={icon}
                      className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
                    >
                      <Icon name={icon} size={20} />
                    </div>
                  ))}
                </div>
              </div>
            </Section>

            <Section id="delete-button" title="Delete Button - moumensoliman">
              <div className="flex items-center gap-6">
                <NativeDelete onConfirm={() => {}} onDelete={() => {}} />
                <p className="text-sm text-muted-foreground">
                  Expands into a lightweight confirmation flow.
                </p>
              </div>
            </Section>

            <Section id="toggle-theme" title="Toggle Theme - larsen66">
              <SwitchToggleThemeDemo />
            </Section>

            <Section id="switch" title="Switch with Description - shadcnspace">
              <SwitchWithDescriptionDemo />
            </Section>

            <Section id="carousel" title="Feature Carousel - larsen66">
              <FeatureCarousel />
            </Section>
          </div>
        </main>
      </div>
    </>
  );
}
