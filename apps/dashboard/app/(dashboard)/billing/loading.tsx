import { Skeleton } from '@/components/ui/skeleton';

export default function Loading() {
  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-2 gap-4">
        {[1, 2].map((i) => <Skeleton key={i} className="h-48" />)}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
