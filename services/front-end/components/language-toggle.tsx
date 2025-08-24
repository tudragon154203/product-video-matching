'use client'

import { useLocale } from 'next-intl'
import { useRouter } from 'next/navigation'
import { usePathname } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { useState, useEffect } from 'react'

const languages = [
  { code: 'vi', name: 'Tiếng Việt', flag: '🇻🇳' },
  { code: 'en', name: 'English', flag: '🇺🇸' }
]

export function LanguageToggle() {
  const locale = useLocale()
  const router = useRouter()
  const pathname = usePathname()
  const [isOpen, setIsOpen] = useState(false)

  // Get current locale from URL as fallback
  const getCurrentLocale = () => {
    if (typeof window !== 'undefined') {
      const path = window.location.pathname
      if (path.startsWith('/en')) return 'en'
      if (path.startsWith('/vi')) return 'vi'
    }
    return locale || 'vi' // fallback to locale hook or default 'vi'
  }

  const currentLocale = getCurrentLocale()

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
    <div className="relative">
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