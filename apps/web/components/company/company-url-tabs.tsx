"use client";

import { startTransition } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { mergeSearchParams } from "@/lib/search-params";
import { track, type TrackEventName } from "@/lib/track";

type CompanyUrlTabsProps = {
  pathname: string;
  currentValue: string;
  paramName: string;
  options: Array<{ value: string; label: string }>;
  eventName?: TrackEventName;
};

export function CompanyUrlTabs({
  pathname,
  currentValue,
  paramName,
  options,
  eventName,
}: CompanyUrlTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  return (
    <Tabs
      value={currentValue}
      onValueChange={(value) => {
        const query = mergeSearchParams(searchParams.toString(), {
          [paramName]: value,
        });

        if (eventName) {
          track(eventName, {
            [paramName]: value,
          });
        }

        startTransition(() => {
          router.push(`${pathname}?${query}`);
        });
      }}
    >
      <TabsList
        variant="underline"
        className="w-fit rounded-full border border-border/70 bg-background/88 p-1"
      >
        {options.map((option) => (
          <TabsTrigger
            key={option.value}
            value={option.value}
            className="rounded-full px-4 py-2 text-sm data-[active]:bg-muted/75 data-[active]:shadow-sm"
          >
            {option.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
