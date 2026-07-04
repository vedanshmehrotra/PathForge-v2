import {
  ActivityFeed,
  CategoryElo,
  RecommendedPreview,
  WeakestPatterns,
} from '@/components/dashboard'

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Skill Overview</h1>
          <p className="text-sm text-muted-foreground">
            Aggregated across tracked patterns from the PathForge engine.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="flex flex-col gap-4 xl:col-span-2">
          <CategoryElo />
          <RecommendedPreview />
        </div>
        <div className="flex flex-col gap-4">
          <WeakestPatterns />
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
