import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export default function Loading() {
  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <Skeleton className="h-7 w-28" />
        <Skeleton className="h-4 w-80 mt-2" />
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} size="sm">
            <CardContent className="flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-lg flex-shrink-0" />
              <div>
                <Skeleton className="h-3 w-24 mb-1.5" />
                <Skeleton className="h-5 w-16" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Table Card */}
      <Card>
        <CardHeader className="border-b">
          <Skeleton className="h-4 w-28" />
          <div className="ml-auto">
            <Skeleton className="h-8 w-32 rounded-md" />
          </div>
        </CardHeader>
        <CardContent className="px-0">
          {/* Table header */}
          <div className="flex items-center gap-4 px-4 py-2.5 border-b">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-20 ml-auto" />
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-20 ml-auto" />
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-3 w-20" />
          </div>
          {/* Table rows */}
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-4 w-16 ml-auto" />
              <div className="flex items-center gap-2">
                <Skeleton className="h-1.5 w-16 rounded-full" />
                <Skeleton className="h-3 w-14" />
              </div>
              <Skeleton className="h-4 w-16 ml-auto" />
              <Skeleton className="h-5 w-16 rounded-full" />
              <div className="flex items-center gap-1.5">
                <Skeleton className="h-1.5 w-1.5 rounded-full" />
                <Skeleton className="h-3.5 w-12" />
              </div>
              <Skeleton className="h-3.5 w-24" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
