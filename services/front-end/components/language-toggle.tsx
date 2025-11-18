'use client'

import { useLocale, useTranslations } from 'next-intl'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

const FlagIcon = ({ code }: { code: string }) => {
  if (code === 'vi') {
    return (
      <svg width="24" height="16" viewBox="0 0 30 20" className="inline-block shrink-0 rounded-sm border border-gray-200">
        <rect width="30" height="20" fill="#DA251D"/>
        <polygon points="15,4 17.5,11 25,11 19,15 21,22 15,17 9,22 11,15 5,11 12.5,11" fill="#FFFF00"/>
      </svg>
    )
  }
  return (
    <svg width="24" height="16" viewBox="0 0 30 20" className="inline-block shrink-0 rounded-sm border border-gray-200">
      <rect width="30" height="20" fill="#B22234"/>
      <rect y="2" width="30" height="2" fill="white"/>
      <rect y="6" width="30" height="2" fill="white"/>
      <rect y="10" width="30" height="2" fill="white"/>
      <rect y="14" width="30" height="2" fill="white"/>
      <rect y="18" width="30" height="2" fill="white"/>
      <rect width="12" height="10" fill="#3C3B6E"/>
    </svg>
  )
}

export function LanguageToggle() {
  const t = useTranslations()
  const locale = useLocale()
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)
  const [currentLocale, setCurrentLocale] = useState(locale)
  const { parentRef: menuRef } = useAutoAnimateList<HTMLDivElement>({ duration: 180 })

  const languages = [
    { code: 'vi', name: t('languages.vietnamese') },
    { code: 'en', name: t('languages.english') }
  ]

  // Update current locale when URL changes
  useEffect(() => {
    const path = window.location.pathname
    if (path.startsWith('/en')) {
      setCurrentLocale('en')
    } else if (path.startsWith('/vi')) {
      setCurrentLocale('vi')
    } else {
      setCurrentLocale(locale || 'vi')
    }
  }, [locale, pathname])

  const handleLanguageChange = (newLocale: string) => {
    // Construct the new path more reliably
    const currentPath = window.location.pathname
    let newPath
    
    // If we're on /vi or /en, replace it
    if (currentPath.startsWith('/vi')) {
      newPath = currentPath.replace('/vi', `/${newLocale}`)
    } else if (currentPath.startsWith('/en')) {
      newPath = currentPath.replace('/en', `/${newLocale}`)
    } else {
      // If no locale in path, add it
      newPath = `/${newLocale}${currentPath}`
    }
    
    window.location.replace(newPath)
    setIsOpen(false)
  }

  const currentLanguage = languages.find(lang => lang.code === currentLocale)

  return (
    <div className="relative" ref={menuRef}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 overflow-visible"
      >
        <span className="flex items-center shrink-0">
          <FlagIcon code={currentLocale} />
        </span>
        <span className="text-sm">{currentLanguage?.name}</span>
      </Button>
      
      {isOpen && (
        <div className="absolute top-full mt-2 right-0 bg-background border rounded-lg shadow-lg z-50 min-w-[160px]">
          {languages.map((language) => (
            <button
              key={language.code}
              onClick={() => handleLanguageChange(language.code)}
              className={`w-full px-4 py-2.5 text-left flex items-center gap-3 hover:bg-accent transition-colors first:rounded-t-lg last:rounded-b-lg ${
                language.code === currentLocale ? 'bg-accent' : ''
              }`}
            >
              <span className="flex items-center shrink-0">
                <FlagIcon code={language.code} />
              </span>
              <span className="text-sm">{language.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
