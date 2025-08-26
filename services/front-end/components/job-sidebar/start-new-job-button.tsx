'use client'

import { Button } from '@/components/ui/button'
import { Search } from 'lucide-react'
import { useTranslations } from 'next-intl'
import Link from 'next/link'

export function StartNewJobButton() {
  const t = useTranslations('jobs')
  
  return (
    <Link href="/">
      <Button variant="default" className="w-full">
        <span>{t('startNew')}</span>
        <Search className="ml-2 h-4 w-4" />
      </Button>
    </Link>
  )
}