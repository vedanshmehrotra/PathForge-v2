import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

type Trend = 'up' | 'down' | 'flat'

function normalize(data: number[], width: number, height: number, pad = 2) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const step = data.length > 1 ? (width - pad * 2) / (data.length - 1) : 0
  return data.map((v, i) => {
    const x = pad + i * step
    const y = pad + (height - pad * 2) * (1 - (v - min) / range)
    return [x, y] as const
  })
}

export function Sparkline({
  data,
  width = 96,
  height = 28,
  className,
  color = 'currentColor',
}: {
  data: number[]
  width?: number
  height?: number
  className?: string
  color?: string
}) {
  const pts = normalize(data, width, height)
  const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ')
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path d={d} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  )
}

export function AreaChart({
  data,
  height = 160,
  className,
  showAxis = true,
  labels,
}: {
  data: number[]
  height?: number
  className?: string
  showAxis?: boolean
  labels?: [string, string]
}) {
  const width = 600
  const pts = normalize(data, width, height, 6)
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ')
  const area = `${line} L${pts[pts.length - 1][0]},${height} L${pts[0][0]},${height} Z`
  const min = Math.min(...data)
  const max = Math.max(...data)
  const id = `grad-${Math.round(pts[0][1] * 100)}-${data.length}`

  return (
    <div className={cn('w-full', className)}>
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full"
          style={{ height }}
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0.25, 0.5, 0.75].map((g) => (
            <line
              key={g}
              x1="0"
              x2={width}
              y1={height * g}
              y2={height * g}
              stroke="var(--color-border)"
              strokeWidth="1"
            />
          ))}
          <path d={area} fill={`url(#${id})`} />
          <path
            d={line}
            fill="none"
            stroke="var(--color-primary)"
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        </svg>
        <div className="pointer-events-none absolute right-1 top-0 font-mono text-[10px] text-muted-foreground">
          {max}
        </div>
        <div className="pointer-events-none absolute bottom-0 right-1 font-mono text-[10px] text-muted-foreground">
          {min}
        </div>
      </div>
      {showAxis && labels && (
        <div className="mt-1.5 flex justify-between font-mono text-[10px] text-muted-foreground">
          <span>{labels[0]}</span>
          <span>{labels[1]}</span>
        </div>
      )}
    </div>
  )
}

export function TrendPill({ value, trend }: { value: number; trend: Trend }) {
  const Icon = trend === 'up' ? ArrowUpRight : trend === 'down' ? ArrowDownRight : Minus
  const color =
    trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground'
  return (
    <span className={cn('inline-flex items-center gap-0.5 font-mono text-xs tabular-nums', color)}>
      <Icon className="size-3" />
      {value > 0 ? `+${value}` : value}
    </span>
  )
}

export function Meter({ value, max = 100, className }: { value: number; max?: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-secondary', className)}>
      <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
    </div>
  )
}
