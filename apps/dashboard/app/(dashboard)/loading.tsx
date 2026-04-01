import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export default function Loading() {
  return (
    <>
      {/* Stats Row */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 flex-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent>
                <Skeleton className="h-3 w-24 mb-2" />
                <Skeleton className="h-6 w-20 mb-1" />
                <Skeleton className="h-3 w-16" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="flex flex-wrap lg:flex-col gap-2 lg:justify-center">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-44 rounded-full" />
          ))}
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-4 mt-4">
        {/* Left - Transaction Feed */}
        <Card>
          <CardHeader className="border-b">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-24 mt-1" />
          </CardHeader>
          <CardContent className="space-y-0 divide-y">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 py-3">
                <Skeleton className="h-1.5 w-1.5 rounded-full flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <Skeleton className="h-3.5 w-36 mb-1.5" />
                  <div className="flex items-center gap-1.5">
                    <Skeleton className="h-4 w-14 rounded" />
                    <Skeleton className="h-4 w-12 rounded" />
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <Skeleton className="h-3.5 w-16 mb-1" />
                  <Skeleton className="h-3 w-10 ml-auto" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Right - 2x2 Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Payment Types Donut */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="flex items-center gap-4">
              <Skeleton className="w-24 h-24 rounded-full flex-shrink-0" />
              <div className="space-y-2 flex-1">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="w-2 h-2 rounded-full" />
                    <Skeleton className="h-3 w-20" />
                    <Skeleton className="h-3 w-8 ml-auto" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Network Health */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-2.5">
                  <Skeleton className="h-1.5 w-1.5 rounded-full flex-shrink-0" />
                  <Skeleton className="h-3.5 w-16 flex-1" />
                  <Skeleton className="h-3 w-10" />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* 7-Day Volume */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-28 w-full rounded" />
            </CardContent>
          </Card>

          {/* Volume by Chain */}
          <Card>
            <CardHeader>
              <Skeleton className="h-4 w-28" />
            </CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-3 w-12" />
                  </div>
                  <Skeleton className="h-1.5 w-full rounded-full" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent Activity Table */}
      <Card>
        <CardHeader>
          <Skeleton className="h-4 w-28" />
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            {/* Table header */}
            <div className="flex gap-4 py-2 border-b">
              <Skeleton className="h-3 w-12" />
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-3 w-16 ml-auto" />
              <Skeleton className="h-3 w-14" />
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-3 w-12" />
            </div>
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 py-3 border-b last:border-0">
                <Skeleton className="h-3.5 w-16" />
                <Skeleton className="h-3.5 w-40" />
                <Skeleton className="h-3.5 w-20 ml-auto" />
                <Skeleton className="h-5 w-16 rounded" />
                <Skeleton className="h-5 w-18 rounded" />
                <Skeleton className="h-3.5 w-12" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* QuickStart Strip */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-44" />
            <Skeleton className="h-3.5 w-3.5" />
          </div>
          <Skeleton className="h-3 w-20 mt-1" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-lg border p-3">
                <Skeleton className="w-5 h-5 rounded-full flex-shrink-0" />
                <Skeleton className="h-3.5 w-32" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  )
}
