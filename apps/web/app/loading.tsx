import { Skeleton } from "@/components/ui/skeleton";

export default function RootLoading() {
  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-14 sm:px-6 lg:px-10">
      <Skeleton className="h-4 w-44 rounded-full" />
      <Skeleton className="h-[26rem] rounded-[2rem]" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Skeleton className="h-40 rounded-[1.5rem]" />
        <Skeleton className="h-40 rounded-[1.5rem]" />
        <Skeleton className="h-40 rounded-[1.5rem]" />
        <Skeleton className="h-40 rounded-[1.5rem]" />
      </div>
    </div>
  );
}
