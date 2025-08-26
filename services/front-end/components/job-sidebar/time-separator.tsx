'use client'

export function TimeSeparator({ label }: { label: string }) {
  return (
    <div className="flex items-center py-2 px-1">
      <div className="flex-1 h-px bg-gray-300"></div>
      <span className="px-3 text-xs text-gray-500 font-medium">{label}</span>
      <div className="flex-1 h-px bg-gray-300"></div>
    </div>
  )
}