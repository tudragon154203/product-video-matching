'use client'

import { useLocale, useTranslations } from 'next-intl'
import { useRouter } from 'next/navigation'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

export function LanguageToggle() {
  const t = useTranslations()
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)
  const [currentLocale, setCurrentLocale] = useState(locale)
  const { parentRef: menuRef } = useAutoAnimateList<HTMLDivElement>({ duration: 180 })

  const languages = [
    { code: 'vi', name: t('languages.vietnamese'), flag: '🇻🇳' },
    { code: 'en', name: t('languages.english'), flag: '🇺🇸' }
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
        className="flex items-center space-x-2"
      >
        <span>{currentLanguage?.flag}</span>
        <span>{currentLanguage?.name}</span>
      </Button>
      
      {isOpen && (
        <div className="absolute top-full mt-2 right-0 bg-white border rounded-lg shadow-lg z-50 min-w-[120px]">
          {languages.map((language) => (
            <button
              key={language.code}
              onClick={() => handleLanguageChange(language.code)}
              className={`w-full px-4 py-2 text-left flex items-center space-x-2 hover:bg-gray-100 ${
                language.code === currentLocale ? 'bg-gray-100' : ''
              }`}
            >
              <span>{language.flag}</span>
              <span>{language.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
