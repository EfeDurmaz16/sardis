import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardHeader } from "@/components/ui/card"

export default function Loading() {
  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-4 w-72 mt-2" />
      </div>

      {/* Organization Card */}
      <Card>
        <CardHeader className="border-b">
          <Skeleton className="h-4 w-24" />
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-9 w-full rounded-md" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-9 w-full rounded-md" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications Card */}
      <Card>
        <CardHeader className="border-b">
          <Skeleton className="h-4 w-28" />
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <Skeleton className="h-4 w-36 mb-1" />
                  <Skeleton className="h-3 w-56" />
                </div>
                <Skeleton className="h-5 w-9 rounded-full" />
              </div>
              {i < 2 && <Skeleton className="h-px w-full mt-4" />}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Security Card */}
      <Card>
        <CardHeader className="border-b">
          <Skeleton className="h-4 w-20" />
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i}>
              <div className="flex items-center justify-between">
                <div>
                  <Skeleton className="h-4 w-44 mb-1" />
                  <Skeleton className="h-3 w-64" />
                </div>
                {i === 1 ? (
                  <Skeleton className="h-9 w-32 rounded-md" />
                ) : (
                  <Skeleton className="h-5 w-9 rounded-full" />
                )}
              </div>
              {i < 2 && <Skeleton className="h-px w-full mt-4" />}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Save button */}
      <div className="flex justify-end">
        <Skeleton className="h-9 w-28 rounded-md" />
      </div>
    </div>
  )
}
