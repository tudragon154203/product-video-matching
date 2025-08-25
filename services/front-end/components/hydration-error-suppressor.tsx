'use client'

import { useEffect } from 'react'

// Suppress hydration errors immediately when this module loads
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  const originalError = console.error
  
  console.error = (...args) => {
    // Convert all arguments to strings for checking, including Error objects
    const errorString = args.map(arg => {
      if (arg instanceof Error) {
        return arg.message + ' ' + (arg.stack || '')
      }
      return String(arg)
    }).join(' ')
    
    // Filter out hydration-related errors with comprehensive patterns
    if (
      errorString.includes('Text content did not match') ||
      errorString.includes('hydration') ||
      errorString.includes('server-rendered HTML') ||
      errorString.includes('An error occurred during hydration') ||
      errorString.includes('react-hydration-error') ||
      errorString.includes('nextjs.org/docs/messages/react-hydration-error') ||
      (errorString.includes('Server:') && errorString.includes('Client:')) ||
      errorString.includes('Because the error happened outside of a Suspense boundary') ||
      errorString.includes('The server HTML was replaced with client content')
    ) {
      return // Suppress these specific errors
    }
    
    // Allow all other errors to show normally
    originalError.call(console, ...args)
  }
}

export function HydrationErrorSuppressor() {
  // This component renders nothing visible
  return null
}