'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { StartJobRequest } from '@/lib/zod/job'
import { jobApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from '@/components/ui/use-toast'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslations, useLocale } from 'next-intl'

export function StartJobForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const queryClient = useQueryClient()
  const t = useTranslations('jobs')
  const tForm = useTranslations('form')
  const tCommon = useTranslations('common')
  const tToast = useTranslations('toast')
  const locale = useLocale()

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const form = (e.target as HTMLInputElement).form
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true }))
      }
    }
  }

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<StartJobRequest>({
    resolver: zodResolver(StartJobRequest),
    defaultValues: {
      query: '',
      top_amz: 10,
      top_ebay: 5,
      platforms: ['youtube'],
      recency_days: 365,
    },
  })

  const onSubmit = async (data: StartJobRequest) => {
    setIsSubmitting(true)
    try {
      const response = await jobApi.startJob(data)
      toast({
        title: tToast('jobStarted'),
        description: tToast('jobStartedDescription', { jobId: response.job_id }),
      })
      reset()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    } catch (error) {
      toast({
        title: tToast('failedToStartJob'),
        description: error instanceof Error ? error.message : tToast('unknownError'),
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const [showAdvanced, setShowAdvanced] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('startNew')}</CardTitle>
        <CardDescription>
          {t('startNewDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Search Bar with Button */}
          <div className="flex space-x-2">
            <div className="flex-1 space-y-2">
              <Label htmlFor="query">{t('query')}</Label>
              <Input
                id="query"
                {...register('query')}
                placeholder={t('queryPlaceholder')}
                required
                onKeyPress={handleKeyPress}
              />
              {errors.query && (
                <p className="text-sm text-red-500">{errors.query.message}</p>
              )}
            </div>
            <Button 
              type="submit" 
              disabled={isSubmitting}
              className="h-10 px-6"
            >
              {isSubmitting ? t('startingJob') : tCommon('search')}
            </Button>
          </div>

          {/* Advanced Options */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>{showAdvanced ? 'Hide' : 'Show'} Advanced Options</span>
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
                    <Label htmlFor="top_amz">{t('topAmazonProducts')}</Label>
                    <Input
                      id="top_amz"
                      type="number"
                      {...register('top_amz', { valueAsNumber: true })}
                      min="1"
                      max="100"
                      defaultValue={10}
                    />
                    {errors.top_amz && (
                      <p className="text-sm text-red-500">{errors.top_amz.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="top_ebay">{t('topEbayProducts')}</Label>
                    <Input
                      id="top_ebay"
                      type="number"
                      {...register('top_ebay', { valueAsNumber: true })}
                      min="1"
                      max="100"
                      defaultValue={5}
                    />
                    {errors.top_ebay && (
                      <p className="text-sm text-red-500">{errors.top_ebay.message}</p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="platforms">{t('videoPlatforms')}</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {['youtube', 'douyin', 'tiktok', 'bilibili'].map((platform) => (
                      <label key={platform} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          value={platform}
                          {...register('platforms')}
                          defaultChecked={platform === 'youtube'}
                          className="rounded border-gray-300"
                        />
                        <span className="capitalize">{platform}</span>
                      </label>
                    ))}
                  </div>
                  {errors.platforms && (
                    <p className="text-sm text-red-500">{errors.platforms.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="recency_days">{t('recencyDays')}</Label>
                  <Input
                    id="recency_days"
                    type="number"
                    {...register('recency_days', { valueAsNumber: true })}
                    min="1"
                    max="365"
                    defaultValue={365}
                  />
                  {errors.recency_days && (
                    <p className="text-sm text-red-500">{errors.recency_days.message}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}