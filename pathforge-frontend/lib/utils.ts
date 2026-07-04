import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getInitials(name: string): string {
  return (
    name
      .split(/\s+/)
      .map((w) => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || '??'
  )
}
