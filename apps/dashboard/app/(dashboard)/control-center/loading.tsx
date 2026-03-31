import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export default function Loading() {
  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <Skeleton className="h-7 w-36" />
        <Skeleton className="h-4 w-72 mt-2" />
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

      {/* 2-col: Controls + Threats */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Security Controls */}
        <Card>
          <CardHeader className="border-b">
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="divide-y">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center justify-between gap-4 py-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-8 w-8 rounded-lg flex-shrink-0" />
                  <div>
                    <Skeleton className="h-4 w-36 mb-1" />
                    <Skeleton className="h-3 w-56" />
                  </div>
                </div>
                <Skeleton className="h-5 w-9 rounded-full flex-shrink-0" />
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Threat Overview */}
        <Card>
          <CardHeader className="border-b">
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="divide-y">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-start gap-3 py-3">
                <Skeleton className="mt-1.5 h-1.5 w-1.5 rounded-full flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <Skeleton className="h-4 w-full max-w-xs mb-1" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Active Blocks Table */}
      <Card>
        <CardHeader className="border-b">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="px-0">
          {/* Table header */}
          <div className="flex items-center gap-4 px-4 py-2.5 border-b">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-3 w-14" />
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-3 w-24" />
          </div>
          {/* Table rows */}
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-0">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="h-5 w-20 rounded-full" />
              <Skeleton className="h-3.5 w-40" />
              <Skeleton className="h-3.5 w-28" />
              <Skeleton className="h-3.5 w-28" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
