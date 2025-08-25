import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export * from './utils/formatDuration'
export * from './utils/formatGMT7'
export * from './utils/groupBy'