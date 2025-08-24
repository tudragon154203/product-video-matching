'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { StartJobRequest } from '@/lib/zod/job'
import { jobApi } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { toast } from '@/components/ui/use-toast'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslations, useLocale } from 'next-intl'
import { AdvancedOptions } from '@/components/advanced-options'

export function StartJobForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const queryClient = useQueryClient()
  const t = useTranslations('jobs')
  const tCommon = useTranslations('common')
  const tToast = useTranslations('toast')
  const locale = useLocale()

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const form = (e.target as HTMLInputElement).form;
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true }));
      }
    }
  };

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
  } = useForm<StartJobRequest>({
    resolver: zodResolver(StartJobRequest),
    defaultValues: {
      query: '',
      top_amz: 10,
      top_ebay: 5,
      platforms: ['youtube', 'douyin', 'tiktok', 'bilibili'],
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

  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle className="text-2xl font-bold">{t('startNew')}</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Search Bar with Button */}
          <div className="flex space-x-2">
            <Input
              id="query"
              {...register('query')}
              placeholder={t('queryPlaceholder')}
              required
              onKeyPress={handleKeyPress}
              className="flex-1 text-lg h-12"
            />
            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-12 px-6 text-lg"
            >
              {isSubmitting ? t('startingJob') : tCommon('search')}
            </Button>
          </div>
          {errors.query && (
            <p className="text-sm text-red-500">{errors.query.message}</p>
          )}

          {/* Advanced Options */}
          <AdvancedOptions
            register={register}
            errors={errors}
            setValue={setValue}
            watch={watch}
          />
        </form>
      </CardContent>
    </Card>
  )
}