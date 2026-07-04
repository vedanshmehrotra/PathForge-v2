import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function StatTile({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  className,
}: {
  label: string
  value: string | number
  sub?: React.ReactNode
  icon?: LucideIcon
  accent?: boolean
  className?: string
}) {
  return (
    <div
      className={cn(
        'flex flex-col gap-1 rounded-lg border border-border bg-card p-3.5',
        className,
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        {Icon && (
          <Icon className={cn('size-3.5', accent ? 'text-primary' : 'text-muted-foreground')} />
        )}
      </div>
      <span className="font-mono text-2xl font-semibold tabular-nums leading-none tracking-tight">
        {value}
      </span>
      {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  )
}
