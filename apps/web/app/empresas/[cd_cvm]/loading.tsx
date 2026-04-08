import { Skeleton } from "@/components/ui/skeleton";

export default function EmpresaDetailLoading() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-12 sm:px-6 lg:px-10">
      <div className="space-y-4">
        <Skeleton className="h-4 w-64 rounded-full" />
        <Skeleton className="h-32 rounded-[1.75rem]" />
      </div>
      <Skeleton className="h-28 rounded-[1.5rem]" />
      <Skeleton className="h-10 w-60 rounded-full" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-36 rounded-[1.4rem]" />
        <Skeleton className="h-36 rounded-[1.4rem]" />
        <Skeleton className="h-36 rounded-[1.4rem]" />
        <Skeleton className="h-36 rounded-[1.4rem]" />
      </div>
      <Skeleton className="h-96 rounded-[1.75rem]" />
    </div>
  );
}
