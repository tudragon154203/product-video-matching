'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Toaster } from '@/components/ui/toaster'
import ProgressBar from 'nextjs-progressbar'

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
          delay: 100
        }}
        startPosition={0}
        stopDelayMs={400}
        showOnShallow={false}
      />
      
      <QueryClientProvider client={queryClient}>
        {children}
        <Toaster />
      </QueryClientProvider>
    </>
  )
}