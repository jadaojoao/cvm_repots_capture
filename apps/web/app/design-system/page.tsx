"use client";

import dynamic from "next/dynamic";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CheckboxGroup } from "@/components/ui/checkbox-group";
import { Calendar } from "@/components/calendar";
import { Textarea } from "@/components/ui/textarea";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionPanel,
} from "@/components/coss-accordion";
import { Field, FieldLabel, FieldItem, FieldError } from "@/components/ui/field";
import { Toolbar, ToolbarButton, ToolbarGroup } from "@/components/ui/toolbar";
import { Tabs, TabsList, TabsTab, TabsPanel } from "@/components/ui/tabs";
import SwitchToggleThemeDemo from "@/components/toggle-theme";
import ContentTooltipDemo from "@/components/contemt-tooltip";
import SwitchWithDescriptionDemo from "@/components/with-description";
import AnimatedDropdown from "@/components/ui/animated-dropdown";
import InteractiveHoverButton from "@/components/ui/interactive-hover-button";
import { NativeDelete } from "@/components/delete-button";
import { Home, Search, BarChart2, Bookmark, User } from "lucide-react";
import { InteractiveMenu } from "@/components/modern-mobile-menu";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";

const FeatureCarousel = dynamic(() => import("@/components/feature-carousel"), {
  ssr: false,
  loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" />,
});
const FinancialTable = dynamic(
  () => import("@/components/financial-markets-table").then((m) => ({ default: m.FinancialTable })),
  { ssr: false, loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" /> },
);
const LeadsTable = dynamic(
  () => import("@/components/leads-data-table").then((m) => ({ default: m.LeadsTable })),
  { ssr: false, loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" /> },
);
const ServerManagementTable = dynamic(
  () => import("@/components/server-management-table").then((m) => ({ default: m.ServerManagementTable })),
  { ssr: false, loading: () => <div className="h-48 animate-pulse rounded-xl bg-muted" /> },
);
const IncidentSummaryCard = dynamic(() => import("@/components/horizontal-bar-chart"), {
  ssr: false,
  loading: () => <div className="h-64 animate-pulse rounded-xl bg-muted" />,
});
const AdvancedIncidentReportCard = dynamic(() => import("@/components/area-chart-medium"), {
  ssr: false,
  loading: () => <div className="h-64 animate-pulse rounded-xl bg-muted" />,
});

function Icon({ name, size = 24, className }: { name: string; size?: number; className?: string }) {
  return (
    <span
      className={cn("material-symbols-outlined select-none leading-none", className)}
      style={{ fontSize: size, fontVariationSettings: "'wght' 200" }}
    >
      {name}
    </span>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 space-y-5">
      <div className="border-b border-border pb-3">
        <h2 className="font-heading text-2xl font-semibold tracking-tight">{title}</h2>
      </div>
      <div className="rounded-xl border border-border bg-card p-8">{children}</div>
    </section>
  );
}

const NAV = [
  { group: "Foundation", items: [
    { label: "UI Colors", href: "#colors" },
    { label: "Chart Palette", href: "#chart-colors" },
    { label: "Spacing", href: "#spacing" },
    { label: "Typography", href: "#typography" },
    { label: "Border Radius", href: "#radius" },
  ]},
  { group: "Data Viz", items: [
    { label: "Charts", href: "#charts" },
    { label: "Tables", href: "#tables" },
  ]},
  { group: "Navigation", items: [
    { label: "Tabs", href: "#tabs" },
    { label: "Toolbar", href: "#toolbar" },
    { label: "Dropdown", href: "#dropdown" },
    { label: "Mobile Menu", href: "#mobile-menu" },
  ]},
  { group: "Forms", items: [
    { label: "Field", href: "#field" },
    { label: "Inputs", href: "#inputs" },
    { label: "Textarea", href: "#textarea" },
    { label: "Checkbox", href: "#checkbox" },
    { label: "Calendar", href: "#calendar" },
  ]},
  { group: "Feedback", items: [
    { label: "Accordion", href: "#accordion" },
    { label: "Tooltip", href: "#tooltip" },
  ]},
  { group: "Actions", items: [
    { label: "Buttons", href: "#buttons" },
    { label: "Icons", href: "#icons" },
    { label: "Delete Button", href: "#delete-button" },
  ]},
  { group: "Utilities", items: [
    { label: "Toggle Theme", href: "#toggle-theme" },
    { label: "Switch", href: "#switch" },
  ]},
  { group: "Marketing", items: [
    { label: "Feature Carousel", href: "#carousel" },
  ]},
];

export default function DesignSystemPage() {
  return (
    <>
      <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,200,0,0" />

      <div className="flex min-h-screen">
        {/* Sidebar */}
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

        {/* Main content */}
        <main className="flex-1 px-6 py-12 lg:px-16 xl:px-20">
          <div className="mx-auto max-w-4xl space-y-24">

            {/* Header */}
            <div className="space-y-3">
              <h1 className="font-heading text-5xl font-bold tracking-tight">Design System</h1>
              <p className="max-w-xl text-lg text-muted-foreground">
                Tokens, componentes e padrões visuais do CVM Analytics — Tailwind v4, OkLch, Material Symbols, 21st.dev.
              </p>
            </div>

            {/* UI COLORS */}
            <Section id="colors" title="UI Colors">
              <div className="grid grid-cols-2 gap-5 sm:grid-cols-4">
                {[
                  { name: "Background", cls: "bg-background border border-border" },
                  { name: "Foreground", cls: "bg-foreground" },
                  { name: "Primary", cls: "bg-primary" },
                  { name: "Secondary", cls: "bg-secondary border border-border/40" },
                  { name: "Muted", cls: "bg-muted border border-border/40" },
                  { name: "Accent", cls: "bg-accent border border-border/40" },
                  { name: "Destructive", cls: "bg-destructive" },
                  { name: "Border", cls: "border-4 border-border bg-background" },
                ].map((c) => (
                  <div key={c.name} className="space-y-2">
                    <div className={cn("h-20 w-full rounded-md", c.cls)} />
                    <p className="text-sm font-medium">{c.name}</p>
                  </div>
                ))}
              </div>
            </Section>

            {/* CHART PALETTE */}
            <Section id="chart-colors" title="Chart Palette">
              <p className="mb-5 text-sm text-muted-foreground">
                Hues espaçados ~72° no círculo OkLch · chroma real em light e dark mode.
              </p>
              <div className="space-y-4">
                {[
                  { name: "Chart 1 — Teal", token: "--chart-1", hue: "161°", note: "Primária / brand" },
                  { name: "Chart 2 — Amber", token: "--chart-2", hue: "29°", note: "Contraste complementar" },
                  { name: "Chart 3 — Blue-Violet", token: "--chart-3", hue: "258°", note: "" },
                  { name: "Chart 4 — Lime", token: "--chart-4", hue: "79°", note: "" },
                  { name: "Chart 5 — Rose", token: "--chart-5", hue: "320°", note: "" },
                ].map((c, i) => (
                  <div key={c.token} className="flex items-center gap-4">
                    <div className="h-8 w-8 shrink-0 rounded-md" style={{ backgroundColor: `var(${c.token})` }} />
                    <div className="w-48">
                      <p className="text-sm font-medium">{c.name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{c.token} · {c.hue}</p>
                    </div>
                    <div className="h-2 flex-1 rounded-full opacity-80" style={{ backgroundColor: `var(${c.token})` }} />
                    {c.note && <span className="text-xs text-muted-foreground">{c.note}</span>}
                  </div>
                ))}
              </div>
            </Section>

            {/* SPACING */}
            <Section id="spacing" title="Spacing">
              <div className="space-y-3">
                {[{ t: "1", px: 4 }, { t: "2", px: 8 }, { t: "4", px: 16 }, { t: "8", px: 32 }, { t: "12", px: 48 }, { t: "16", px: 64 }, { t: "20", px: 80 }, { t: "24", px: 96 }].map((s) => (
                  <div key={s.t} className="flex items-center gap-4">
                    <span className="w-24 shrink-0 font-mono text-xs text-muted-foreground">space-{s.t} · {s.px}px</span>
                    <div className="h-5 rounded-sm bg-primary/25" style={{ width: s.px }} />
                  </div>
                ))}
              </div>
            </Section>

            {/* TYPOGRAPHY */}
            <Section id="typography" title="Typography">
              <div className="space-y-10">
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">Space Grotesk — heading</p>
                  <p className="font-heading text-5xl font-bold tracking-tight">The quick brown fox</p>
                  <p className="font-heading text-3xl font-semibold">jumps over the lazy dog</p>
                  <p className="font-heading text-xl font-medium">0123456789 AaBbCcDd</p>
                </div>
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">Manrope — body</p>
                  <p className="text-base leading-relaxed text-foreground">Plataforma pública de análise financeira com dados da CVM para descoberta rápida, leitura histórica e navegação por 449+ empresas listadas.</p>
                  <p className="text-sm leading-relaxed text-muted-foreground">Texto secundário, descrições, metadados de interface.</p>
                  <p className="text-xs text-muted-foreground/70">Texto terciário, labels, cabeçalhos de tabela.</p>
                </div>
                <div className="space-y-2">
                  <p className="font-mono text-xs text-muted-foreground">IBM Plex Mono — mono</p>
                  <p className="font-mono text-sm">import &#123; CVMQueryLayer &#125; from "@/src/query_layer"</p>
                  <p className="font-mono text-xs text-muted-foreground">LINE_ID_BASE · CD_CONTA · PERIODO_LABEL</p>
                </div>
              </div>
            </Section>

            {/* BORDER RADIUS */}
            <Section id="radius" title="Border Radius">
              <div className="flex flex-wrap gap-6">
                {[
                  { label: "none", cls: "rounded-none" },
                  { label: "sm", cls: "rounded-sm" },
                  { label: "md", cls: "rounded-md ring-2 ring-primary/50 ring-offset-2 ring-offset-card" },
                  { label: "lg", cls: "rounded-lg" },
                  { label: "xl", cls: "rounded-xl" },
                  { label: "2xl", cls: "rounded-2xl" },
                  { label: "full", cls: "rounded-full" },
                ].map((r) => (
                  <div key={r.label} className="flex flex-col items-center gap-2">
                    <div className={cn("h-14 w-14 border-2 border-primary/40 bg-primary/10", r.cls)} />
                    <span className="font-mono text-xs text-muted-foreground">{r.label}{r.label === "md" ? " ← base" : ""}</span>
                  </div>
                ))}
              </div>
            </Section>

            {/* CHARTS */}
            <Section id="charts" title="Charts — reaviz">
              <div className="space-y-10">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Horizontal Bar Chart</p>
                  <IncidentSummaryCard />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Area Chart (multi-series)</p>
                  <AdvancedIncidentReportCard />
                </div>
              </div>
            </Section>

            {/* TABLES */}
            <Section id="tables" title="Tables">
              <div className="space-y-12">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Financial Markets Table</p>
                  <FinancialTable />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Leads Data Table</p>
                  <LeadsTable />
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Server Management Table</p>
                  <ServerManagementTable />
                </div>
              </div>
            </Section>

            {/* TABS */}
            <Section id="tabs" title="Tabs — coss.com">
              <Tabs defaultValue="overview">
                <TabsList>
                  <TabsTab value="overview">Visão Geral</TabsTab>
                  <TabsTab value="analytics">Análise</TabsTab>
                  <TabsTab value="reports">Relatórios</TabsTab>
                  <TabsTab value="settings" disabled>Configurações</TabsTab>
                </TabsList>
                <TabsPanel value="overview" className="mt-4 text-sm text-muted-foreground">Conteúdo da aba Visão Geral — KPIs, sumário.</TabsPanel>
                <TabsPanel value="analytics" className="mt-4 text-sm text-muted-foreground">Conteúdo da aba Análise — gráficos, comparativos.</TabsPanel>
                <TabsPanel value="reports" className="mt-4 text-sm text-muted-foreground">Conteúdo da aba Relatórios — demonstrações, export.</TabsPanel>
              </Tabs>
            </Section>

            {/* TOOLBAR */}
            <Section id="toolbar" title="Toolbar — coss.com">
              <Toolbar>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Bold"><Icon name="format_bold" size={18} /></ToolbarButton>
                  <ToolbarButton aria-label="Italic"><Icon name="format_italic" size={18} /></ToolbarButton>
                  <ToolbarButton aria-label="Underline"><Icon name="format_underlined" size={18} /></ToolbarButton>
                </ToolbarGroup>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Align left"><Icon name="format_align_left" size={18} /></ToolbarButton>
                  <ToolbarButton aria-label="Align center"><Icon name="format_align_center" size={18} /></ToolbarButton>
                  <ToolbarButton aria-label="Align right"><Icon name="format_align_right" size={18} /></ToolbarButton>
                </ToolbarGroup>
                <ToolbarGroup>
                  <ToolbarButton aria-label="Filter"><Icon name="filter_list" size={18} /></ToolbarButton>
                  <ToolbarButton aria-label="Download"><Icon name="download" size={18} /></ToolbarButton>
                </ToolbarGroup>
              </Toolbar>
            </Section>

            {/* DROPDOWN */}
            <Section id="dropdown" title="Animated Dropdown — Shatlyk1011">
              <div className="flex gap-4">
                <AnimatedDropdown
                  text="Exportar"
                  items={[
                    { name: "Excel (.xlsx)", link: "#" },
                    { name: "CSV", link: "#" },
                    { name: "PDF", link: "#" },
                  ]}
                />
                <AnimatedDropdown
                  text="Ações"
                  items={[
                    { name: "Comparar", link: "#" },
                    { name: "Compartilhar", link: "#" },
                    { name: "Configurações", link: "#" },
                  ]}
                />
              </div>
            </Section>

            {/* MOBILE MENU */}
            <Section id="mobile-menu" title="Mobile Navigation — easemize">
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

            {/* FIELD */}
            <Section id="field" title="Field — coss.com">
              <div className="grid max-w-lg gap-5 sm:grid-cols-2">
                <Field>
                  <FieldLabel>Empresa</FieldLabel>
                  <FieldItem><Input placeholder="Ex: Petrobras" /></FieldItem>
                </Field>
                <Field>
                  <FieldLabel>Ano fiscal</FieldLabel>
                  <FieldItem><Input placeholder="2024" /></FieldItem>
                </Field>
                <Field>
                  <FieldLabel>Campo com erro</FieldLabel>
                  <FieldItem><Input aria-invalid placeholder="CNPJ inválido" /></FieldItem>
                  <FieldError>CNPJ não encontrado na CVM.</FieldError>
                </Field>
                <Field>
                  <FieldLabel>Desabilitado</FieldLabel>
                  <FieldItem><Input disabled placeholder="Indisponível" /></FieldItem>
                </Field>
              </div>
            </Section>

            {/* INPUTS */}
            <Section id="inputs" title="Inputs">
              <div className="flex max-w-sm flex-col gap-4">
                <Input placeholder="Default" />
                <div className="relative">
                  <Icon name="search" size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input placeholder="Search..." className="pl-9" />
                </div>
                <Input aria-invalid placeholder="Estado de erro" />
                <Input disabled placeholder="Desabilitado" />
              </div>
            </Section>

            {/* TEXTAREA */}
            <Section id="textarea" title="Textarea — coss.com">
              <div className="flex max-w-sm flex-col gap-4">
                <Textarea placeholder="Adicione uma observação sobre a empresa..." rows={4} />
                <Textarea placeholder="Desabilitado..." disabled rows={3} />
              </div>
            </Section>

            {/* CHECKBOX */}
            <Section id="checkbox" title="Checkbox Group — coss.com">
              <div className="flex flex-wrap gap-8">
                <div>
                  <p className="mb-3 text-sm font-medium">Demonstrações</p>
                  <CheckboxGroup className="gap-3">
                    {["DRE", "BPA", "BPP", "DFC", "DVA"].map((item) => (
                      <div key={item} className="flex items-center gap-2">
                        <Checkbox id={`chk-${item}`} />
                        <Label htmlFor={`chk-${item}`} className="text-sm">{item}</Label>
                      </div>
                    ))}
                  </CheckboxGroup>
                </div>
              </div>
            </Section>

            {/* CALENDAR */}
            <Section id="calendar" title="Calendar — coss.com">
              <Calendar />
            </Section>

            {/* ACCORDION */}
            <Section id="accordion" title="Accordion — coss.com">
              <Accordion>
                <AccordionItem value="dfp">
                  <AccordionTrigger>O que é DFP?</AccordionTrigger>
                  <AccordionPanel>
                    Demonstrações Financeiras Padronizadas — relatório anual obrigatório enviado à CVM por companhias abertas.
                  </AccordionPanel>
                </AccordionItem>
                <AccordionItem value="itr">
                  <AccordionTrigger>O que é ITR?</AccordionTrigger>
                  <AccordionPanel>
                    Informações Trimestrais — relatório enviado trimestralmente à CVM com demonstrações financeiras condensadas.
                  </AccordionPanel>
                </AccordionItem>
                <AccordionItem value="kpis">
                  <AccordionTrigger>Como são calculados os KPIs?</AccordionTrigger>
                  <AccordionPanel>
                    Calculados via <code className="rounded bg-muted px-1 font-mono text-xs">kpi_engine.py</code> com 60+ indicadores — ROE, ROA, margens, solvência e liquidez.
                  </AccordionPanel>
                </AccordionItem>
              </Accordion>
            </Section>

            {/* TOOLTIP */}
            <Section id="tooltip" title="Tooltip — larsen66">
              <ContentTooltipDemo />
            </Section>

            {/* BUTTONS */}
            <Section id="buttons" title="Buttons">
              <div className="space-y-6">
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Variants</p>
                  <div className="flex flex-wrap gap-3">
                    <Button>Primary</Button>
                    <Button variant="secondary">Secondary</Button>
                    <Button variant="outline">Outline</Button>
                    <Button variant="ghost">Ghost</Button>
                    <Button variant="destructive">Destructive</Button>
                  </div>
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">Sizes</p>
                  <div className="flex flex-wrap items-center gap-3">
                    <Button size="sm">Small</Button>
                    <Button>Medium</Button>
                    <Button size="lg">Large</Button>
                  </div>
                </div>
                <div>
                  <p className="mb-3 font-mono text-xs text-muted-foreground">States & variants</p>
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

            {/* ICONS */}
            <Section id="icons" title="Icons — Material Symbols Outlined · weight 200">
              <div className="space-y-6">
                <div className="flex flex-wrap items-end gap-5">
                  {[16, 20, 24, 32, 40].map((s) => (
                    <div key={s} className="flex flex-col items-center gap-2">
                      <div className="flex h-14 w-14 items-center justify-center rounded-md border border-border bg-muted">
                        <Icon name="analytics" size={s} />
                      </div>
                      <span className="font-mono text-xs text-muted-foreground">{s}px</span>
                    </div>
                  ))}
                </div>
                <div className="flex flex-wrap gap-2">
                  {["search", "home", "analytics", "trending_up", "business_center", "account_circle", "settings", "notifications", "bookmark", "share", "download", "filter_list", "close", "check_circle", "arrow_forward", "expand_more", "compare", "table_chart", "bar_chart", "show_chart"].map((icon) => (
                    <div key={icon} title={icon} className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground">
                      <Icon name={icon} size={20} />
                    </div>
                  ))}
                </div>
              </div>
            </Section>

            {/* DELETE BUTTON */}
            <Section id="delete-button" title="Delete Button — moumensoliman">
              <div className="flex items-center gap-6">
                <NativeDelete onConfirm={() => {}} onDelete={() => {}} />
                <p className="text-sm text-muted-foreground">Expande para confirmação com animação suave.</p>
              </div>
            </Section>

            {/* TOGGLE THEME */}
            <Section id="toggle-theme" title="Toggle Theme — larsen66">
              <SwitchToggleThemeDemo />
            </Section>

            {/* SWITCH */}
            <Section id="switch" title="Switch with Description — shadcnspace">
              <SwitchWithDescriptionDemo />
            </Section>

            {/* CAROUSEL */}
            <Section id="carousel" title="Feature Carousel — larsen66">
              <FeatureCarousel />
            </Section>

          </div>
        </main>
      </div>
    </>
  );
}
