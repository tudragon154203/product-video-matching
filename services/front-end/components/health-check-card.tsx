'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { jobApi } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { RefreshCw, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'

export function HealthCheckCard() {
  const [isRefreshing, setIsRefreshing] = useState(false)
  
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['health-check'],
    queryFn: () => jobApi.healthCheck(),
    retry: 3,
  })

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await refetch()
    setIsRefreshing(false)
  }

  const getHealthStatus = () => {
    if (isLoading) return { status: 'loading', icon: RefreshCw, color: 'text-blue-600' }
    if (error) return { status: 'error', icon: XCircle, color: 'text-red-600' }
    if (data?.status === 'healthy') return { status: 'healthy', icon: CheckCircle, color: 'text-green-600' }
    return { status: 'warning', icon: AlertTriangle, color: 'text-yellow-600' }
  }

  const healthStatus = getHealthStatus()

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>System Health</CardTitle>
            <CardDescription>
              Monitor the health and status of your services
            </CardDescription>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={isRefreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center space-x-3">
          <healthStatus.icon className={`h-6 w-6 ${healthStatus.color}`} />
          <div>
            <div className="text-lg font-semibold capitalize">
              {healthStatus.status === 'loading' ? 'Checking...' : healthStatus.status}
            </div>
            {data && (
              <div className="text-sm text-muted-foreground">
                Status: {data.status} | Timestamp: {new Date(data.timestamp).toLocaleString()}
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <h4 className="font-medium text-red-800 mb-2">Health Check Failed</h4>
            <p className="text-sm text-red-600">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        )}

        {data && data.status === 'healthy' && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <h4 className="font-medium text-green-800 mb-2">System is Healthy</h4>
            <p className="text-sm text-green-600">
              All services are running normally. Last updated: {new Date(data.timestamp).toLocaleString()}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          <div className="p-4 border rounded-lg">
            <h4 className="font-medium mb-2">Service Status</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm">Main API</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  data?.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {data?.status === 'healthy' ? 'Online' : 'Offline'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm">Frontend</span>
                <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-800">
                  Online
                </span>
              </div>
            </div>
          </div>

          <div className="p-4 border rounded-lg">
            <h4 className="font-medium mb-2">Quick Actions</h4>
            <div className="space-y-2">
              <Button variant="outline" size="sm" onClick={handleRefresh}>
                Refresh Status
              </Button>
              <Button variant="outline" size="sm" asChild>
                <a href="/jobs" target="_blank" rel="noopener noreferrer">
                  View Jobs
                </a>
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}