import {
  PageShell,
  SurfaceCard,
} from "@/components/shared/design-system-recipes";
import { Skeleton } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <PageShell density="relaxed">
      <Skeleton className="h-4 w-44 rounded-full" />
      <SurfaceCard tone="hero" padding="hero">
        <Skeleton className="h-6 w-52 rounded-full" />
        <Skeleton className="mt-6 h-20 w-full rounded-[1.5rem]" />
        <Skeleton className="mt-4 h-14 w-full rounded-[1.25rem]" />
      </SurfaceCard>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-44 rounded-[1.75rem]" />
        <Skeleton className="h-44 rounded-[1.75rem]" />
        <Skeleton className="h-44 rounded-[1.75rem]" />
        <Skeleton className="h-44 rounded-[1.75rem]" />
      </div>
    </PageShell>
  );
}
