"use client"

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
import { Toaster } from '@/components/ui/toaster'
import ProgressBar from 'nextjs-progressbar'
import NProgress from 'nprogress'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 1000 * 60 * 5, // 5 minutes
        refetchOnWindowFocus: false,
      },
    },
  }))

  return (
    <>
            
      <ProgressBar
        height={3}
        color="#3B82F6"
        options={{
          showSpinner: false,
        }}
        // Start at a visible position so the bar shows immediately
        startPosition={0.3}
        // Complete promptly after route settles
        stopDelayMs={200}
        showOnShallow={false}
      />

      <QueryClientProvider client={queryClient}>
        <RouteProgressController />
        {children}
        <Toaster />
      </QueryClientProvider>
    </>
  )
}

function RouteProgressController() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // Finish the progress bar when the route has changed
  useEffect(() => {
    // Small timeout lets layout mount before finishing the bar
    const id = setTimeout(() => NProgress.done(true), 0)
    return () => clearTimeout(id)
  }, [pathname, searchParams])

  // Start progress early on internal link clicks
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      // Only left-click without modifier keys
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
      const target = e.target as HTMLElement | null
      if (!target) return
      const anchor = target.closest('a') as HTMLAnchorElement | null
      if (!anchor) return
      const href = anchor.getAttribute('href')
      const rel = anchor.getAttribute('rel') || ''
      const targetAttr = anchor.getAttribute('target') || ''
      if (!href || href.startsWith('#') || rel.includes('external') || targetAttr === '_blank') return
      try {
        const url = new URL(href, window.location.href)
        // Start only for same-origin navigations
        if (url.origin === window.location.origin) {
          NProgress.set(0.3)
          NProgress.start()
        }
      } catch {
        // Ignore invalid URLs
      }
    }

    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [])

  return null
}
