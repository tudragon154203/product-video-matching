'use client'

import { UseFormRegister, FieldErrors, UseFormSetValue, UseFormWatch } from 'react-hook-form'
import { useState } from 'react'
import { StartJobRequest } from '@/lib/zod/job'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTranslations } from 'next-intl'
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList'

interface AdvancedOptionsProps {
  register: UseFormRegister<StartJobRequest>
  errors: FieldErrors<StartJobRequest>
  setValue: UseFormSetValue<StartJobRequest>
  watch: UseFormWatch<StartJobRequest>
}

export function AdvancedOptions({ register, errors, setValue, watch }: AdvancedOptionsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [selectAllPlatforms, setSelectAllPlatforms] = useState(true)
  const t = useTranslations('jobs')
  const { parentRef: advancedRef } = useAutoAnimateList<HTMLDivElement>()
  const { parentRef: platformsRef } = useAutoAnimateList<HTMLDivElement>()

  const availablePlatforms = ['youtube', 'douyin', 'tiktok', 'bilibili'] as const
  const watchedPlatforms = watch('platforms')

  const handlePlatformChange = (
    platform: (typeof availablePlatforms)[number],
    checked: boolean
  ) => {
    const currentPlatforms = watchedPlatforms || [];
    let newPlatforms: (typeof availablePlatforms)[number][];

    if (checked) {
      newPlatforms = [...currentPlatforms, platform];
    } else {
      newPlatforms = currentPlatforms.filter(
        (p) => p !== platform
      ) as (typeof availablePlatforms)[number][];
    }

    setValue('platforms', newPlatforms);
    
    if (newPlatforms.length === 0) {
      setSelectAllPlatforms(false)
    } else if (newPlatforms.length === availablePlatforms.length) {
      setSelectAllPlatforms(true)
    }
  }

  const handleSelectAllChange = (checked: boolean) => {
    setSelectAllPlatforms(checked)
    if (checked) {
      setValue('platforms', [...availablePlatforms])
    } else {
      setValue('platforms', [])
    }
  }

  const isPlatformChecked = (platform: (typeof availablePlatforms)[number]) => {
    return watchedPlatforms?.includes(platform) || false;
  };

  return (
    <div className="space-y-3" ref={advancedRef}>
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <span>{showAdvanced ? t('hideAdvancedOptions') : t('showAdvancedOptions')}</span>
        <svg
          className={`w-4 h-4 transition-transform ${
            showAdvanced ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {showAdvanced && (
        <div className="space-y-4 pt-3 border-t">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="top_amz">{t('topAmazonProducts')}</Label>
                <div className="group relative">
                  <svg
                    className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="absolute bottom-full left-full ml-2 mb-2 px-3 py-2 bg-black text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-[9999]">
                    {t('topAmazonProductsTooltip')}
                  </div>
                </div>
              </div>
              <Input
                id="top_amz"
                type="number"
                {...register('top_amz', { valueAsNumber: true })}
                min="0"
                max="100"
              />
              {errors.top_amz && (
                <p className="text-sm text-red-500">{errors.top_amz.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="top_ebay">{t('topEbayProducts')}</Label>
                <div className="group relative">
                  <svg
                    className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="absolute bottom-full left-full ml-2 mb-2 px-3 py-2 bg-black text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-[9999]">
                    {t('topEbayProductsTooltip')}
                  </div>
                </div>
              </div>
              <Input
                id="top_ebay"
                type="number"
                {...register('top_ebay', { valueAsNumber: true })}
                min="0"
                max="100"
              />
              {errors.top_ebay && (
                <p className="text-sm text-red-500">{errors.top_ebay.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {/* Video Platforms label and "All" checkbox in same row */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Label htmlFor="platforms">{t('videoPlatforms')}</Label>
                <div className="group relative">
                  <svg
                    className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <div className="absolute bottom-full left-full ml-2 mb-2 px-3 py-2 bg-black text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-[9999]">
                    {t('videoPlatformsTooltip')}
                  </div>
                </div>
              </div>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectAllPlatforms}
                  onChange={(e) => handleSelectAllChange(e.target.checked)}
                  className="rounded border-gray-300"
                />
                <span className="font-medium">All</span>
              </label>
            </div>
            
            {/* Individual platforms only shown when "All" is unchecked */}
            {!selectAllPlatforms && (
              <div className="grid grid-cols-2 gap-2 mt-2" ref={platformsRef}>
                {availablePlatforms.map((platform) => (
                  <label
                    key={platform}
                    className="flex items-center space-x-2 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      value={platform}
                      checked={isPlatformChecked(platform)}
                      onChange={(e) => handlePlatformChange(platform, e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <span className="capitalize">{platform}</span>
                  </label>
                ))}
              </div>
            )}
            {errors.platforms && (
              <p className="text-sm text-red-500">{errors.platforms.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="recency_days">{t('recencyDays')}</Label>
              <div className="group relative">
                <svg
                  className="w-4 h-4 text-gray-400 hover:text-gray-600 cursor-help"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
                    clipRule="evenodd"
                  />
                </svg>
                <div className="absolute bottom-full left-full ml-2 mb-2 px-3 py-2 bg-black text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-[9999]">
                  {t('recencyDaysTooltip')}
                </div>
              </div>
            </div>
            <Input
              id="recency_days"
              type="number"
              {...register('recency_days', { valueAsNumber: true })}
              min="1"
              max="365"
            />
            {errors.recency_days && (
              <p className="text-sm text-red-500">{errors.recency_days.message}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
