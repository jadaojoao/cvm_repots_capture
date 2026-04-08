import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

export const pageShellVariants = cva(
  "mx-auto flex w-full max-w-7xl flex-col px-4 sm:px-6 lg:px-10",
  {
    variants: {
      density: {
        compact: "gap-6 py-10 sm:py-12",
        default: "gap-8 py-12 sm:py-14",
        relaxed: "gap-10 py-14 sm:py-16",
      },
    },
    defaultVariants: {
      density: "default",
    },
  },
);

export function PageShell({
  density,
  className,
  ...props
}: ComponentPropsWithoutRef<"div"> & VariantProps<typeof pageShellVariants>) {
  return (
    <div className={cn(pageShellVariants({ density }), className)} {...props} />
  );
}

export const surfaceVariants = cva(
  "rounded-[1.75rem] border border-border/70 backdrop-blur-sm",
  {
    variants: {
      tone: {
        default:
          "bg-background/92 shadow-[0_24px_70px_-48px_rgba(16,30,24,0.34)]",
        subtle: "bg-background/88 shadow-sm shadow-black/5",
        muted:
          "bg-muted/24 shadow-[0_18px_55px_-48px_rgba(16,30,24,0.18)]",
        hero:
          "bg-background/94 shadow-[0_28px_80px_-52px_rgba(16,30,24,0.38)]",
        inset: "bg-background/82 shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]",
      },
      padding: {
        none: "",
        md: "p-5",
        lg: "p-6 sm:p-7",
        hero: "px-6 py-8 sm:px-8 sm:py-9 lg:px-10 lg:py-10",
      },
    },
    defaultVariants: {
      tone: "default",
      padding: "lg",
    },
  },
);

export function SurfaceCard({
  tone,
  padding,
  className,
  ...props
}: ComponentPropsWithoutRef<"div"> & VariantProps<typeof surfaceVariants>) {
  return (
    <div
      className={cn(surfaceVariants({ tone, padding }), className)}
      {...props}
    />
  );
}

export const infoChipVariants = cva(
  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[0.68rem] font-medium uppercase tracking-[0.18em]",
  {
    variants: {
      tone: {
        default: "border-border/70 bg-background/72 text-muted-foreground",
        brand: "border-primary/15 bg-primary/10 text-primary",
        secondary: "border-secondary/80 bg-secondary text-secondary-foreground",
        muted: "border-border/60 bg-muted/70 text-foreground/78",
      },
    },
    defaultVariants: {
      tone: "default",
    },
  },
);

export function InfoChip({
  tone,
  className,
  ...props
}: ComponentPropsWithoutRef<"span"> & VariantProps<typeof infoChipVariants>) {
  return (
    <span className={cn(infoChipVariants({ tone }), className)} {...props} />
  );
}

type SectionHeadingProps = {
  eyebrow?: ReactNode;
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  titleAs?: "h1" | "h2" | "h3";
  className?: string;
  bodyClassName?: string;
  descriptionClassName?: string;
};

export function SectionHeading({
  eyebrow,
  title,
  description,
  meta,
  titleAs = "h2",
  className,
  bodyClassName,
  descriptionClassName,
}: SectionHeadingProps) {
  const TitleTag = titleAs as ElementType;

  return (
    <div
      className={cn(
        "flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between",
        className,
      )}
    >
      <div className={cn("max-w-3xl space-y-3", bodyClassName)}>
        {eyebrow ? (
          <p className="text-xs uppercase tracking-[0.26em] text-muted-foreground">
            {eyebrow}
          </p>
        ) : null}
        <div className="space-y-3">
          <TitleTag className="font-heading text-4xl tracking-[-0.05em] text-foreground sm:text-5xl">
            {title}
          </TitleTag>
          {description ? (
            <p
              className={cn(
                "text-base leading-8 text-muted-foreground sm:text-lg",
                descriptionClassName,
              )}
            >
              {description}
            </p>
          ) : null}
        </div>
      </div>
      {meta ? (
        <div className="flex shrink-0 items-center gap-3 text-sm text-muted-foreground">
          {meta}
        </div>
      ) : null}
    </div>
  );
}
