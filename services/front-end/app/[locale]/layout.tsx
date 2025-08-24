import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { NextIntlClientProvider } from 'next-intl'
import { getMessages, getTranslations } from 'next-intl/server'
import { Providers } from '@/components/ui/providers'
import { Toaster } from '@/components/ui/toaster'
import { LanguageToggle } from '@/components/language-toggle'
import { JobSidebar } from '@/components/job-sidebar'
import { notFound } from 'next/navigation'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Product Video Matching',
  description: 'Monitor and manage product video matching jobs',
}

const locales = ['vi', 'en']

export default async function LocaleLayout({
  children,
  params: { locale }
}: {
  children: React.ReactNode
  params: { locale: string }
}) {
  if (!locales.includes(locale as any)) notFound()

  const messages = await getMessages({ locale })
  const t = await getTranslations('jobs')

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className={inter.className}>
        <NextIntlClientProvider messages={messages}>
          <Providers>
            <div className="flex h-screen bg-background">
              {/* Sidebar */}
              <div className="w-80 border-r bg-card">
                <div className="flex flex-col h-full">
                  <JobSidebar />
                </div>
              </div>
              
              {/* Main Content */}
              <div className="flex-1 overflow-auto">
                <div className="container mx-auto px-4 py-8">
                  <div className="flex justify-between items-start mb-8">
                    <div>
                      <h1 className="text-2xl font-bold">{t('title')}</h1>
                    </div>
                    <LanguageToggle />
                  </div>
                  {children}
                </div>
                <Toaster />
              </div>
            </div>
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  )
}