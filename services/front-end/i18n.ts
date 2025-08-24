import {getRequestConfig} from 'next-intl/server'
import {notFound} from 'next/navigation'

const locales = ['vi', 'en']

export default getRequestConfig(async ({locale}) => {
  // Handle undefined locale case by defaulting to 'vi'
  if (locale === undefined || locale === null) {
    locale = 'vi'
  }
  
  if (!locales.includes(locale as any)) notFound()

  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default
  } as any
})