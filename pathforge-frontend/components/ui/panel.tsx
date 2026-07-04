import { cn } from '@/lib/utils'

export function Panel({ className, ...props }: React.ComponentProps<'section'>) {
  return (
    <section
      className={cn('flex flex-col rounded-lg border border-border bg-card', className)}
      {...props}
    />
  )
}

export function PanelHeader({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 border-b border-border px-4 py-2.5',
        className,
      )}
      {...props}
    />
  )
}

export function PanelTitle({ className, ...props }: React.ComponentProps<'h3'>) {
  return (
    <h3
      className={cn('flex items-center gap-2 text-sm font-medium text-foreground', className)}
      {...props}
    />
  )
}

export function PanelBody({ className, ...props }: React.ComponentProps<'div'>) {
  return <div className={cn('p-4', className)} {...props} />
}
