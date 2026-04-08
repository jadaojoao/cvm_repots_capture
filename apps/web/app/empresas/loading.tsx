import { Skeleton } from "@/components/ui/skeleton";

export default function EmpresasLoading() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-10">
      <div className="space-y-4">
        <Skeleton className="h-3 w-36 rounded-full" />
        <Skeleton className="h-14 w-full max-w-2xl" />
        <Skeleton className="h-6 w-full max-w-3xl" />
      </div>
      <Skeleton className="h-20 rounded-[1.5rem]" />
      <div className="rounded-[1.75rem] border border-border/60 bg-background/70 p-4">
        <div className="space-y-4">
          <Skeleton className="h-20 rounded-2xl" />
          <Skeleton className="h-20 rounded-2xl" />
          <Skeleton className="h-20 rounded-2xl" />
        </div>
      </div>
    </div>
  );
}
