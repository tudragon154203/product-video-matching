'use client'

import { ReactNode } from 'react'
import Link from 'next/link'

interface SimpleLinkProps {
  href: string
  children: ReactNode
  className?: string
  variant?: 'default' | 'outline'
  size?: 'default' | 'sm'
}

export function SimpleLink({ href, children, className = '', variant = 'default', size = 'default' }: SimpleLinkProps) {
  const baseClasses = 'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50'
  
  const variantClasses = {
    default: 'bg-blue-600 text-white hover:bg-blue-700',
    outline: 'border border-gray-300 bg-white hover:bg-gray-50 hover:text-gray-900'
  }
  
  const sizeClasses = {
    default: 'h-10 px-4 py-2',
    sm: 'h-9 rounded-md px-3'
  }

  return (
    <Link 
      href={href}
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {children}
    </Link>
  )
}