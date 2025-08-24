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

export function StartJobForm() {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const queryClient = useQueryClient()

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
        title: 'Job Started Successfully',
        description: `Job ID: ${response.job_id}`,
      })
      reset()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    } catch (error) {
      toast({
        title: 'Failed to Start Job',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Start New Job</CardTitle>
        <CardDescription>
          Create a new product video matching job
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="query">Query</Label>
            <Input
              id="query"
              {...register('query')}
              placeholder="e.g., ergonomic pillows"
              required
            />
            {errors.query && (
              <p className="text-sm text-red-500">{errors.query.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="top_amz">Top Amazon Products</Label>
              <Input
                id="top_amz"
                type="number"
                {...register('top_amz', { valueAsNumber: true })}
                min="1"
                max="100"
                required
              />
              {errors.top_amz && (
                <p className="text-sm text-red-500">{errors.top_amz.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="top_ebay">Top eBay Products</Label>
              <Input
                id="top_ebay"
                type="number"
                {...register('top_ebay', { valueAsNumber: true })}
                min="1"
                max="100"
                required
              />
              {errors.top_ebay && (
                <p className="text-sm text-red-500">{errors.top_ebay.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="platforms">Video Platforms</Label>
            <div className="grid grid-cols-2 gap-2">
              {['youtube', 'douyin', 'tiktok', 'bilibili'].map((platform) => (
                <label key={platform} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    value={platform}
                    {...register('platforms')}
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
            <Label htmlFor="recency_days">Recency Days</Label>
            <Input
              id="recency_days"
              type="number"
              {...register('recency_days', { valueAsNumber: true })}
              min="1"
              max="365"
              required
            />
            {errors.recency_days && (
              <p className="text-sm text-red-500">{errors.recency_days.message}</p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? 'Starting Job...' : 'Start Job'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}