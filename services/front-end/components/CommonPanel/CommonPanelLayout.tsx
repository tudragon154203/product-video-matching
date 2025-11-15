import React from 'react';
import { PanelHeader } from '@/components/jobs/PanelHeader';
import { PanelSection } from '@/components/jobs/PanelSection';
import { useTranslations } from 'next-intl';
import { useAutoAnimateList } from '@/lib/hooks/useAutoAnimateList';

interface CommonPanelLayoutProps {
  children: React.ReactNode;
  title: string;
  count: number;
  headerChildren?: React.ReactNode;
  footerChildren?: React.ReactNode;
  isPlaceholderData?: boolean;
  isNavigationLoading?: boolean;
  isLoading?: boolean;
  isError?: boolean;
 isEmpty?: boolean;
 error?: Error | null;
  onRetry?: () => void;
  testId?: string;
  skeletonComponent?: React.ReactNode;
  emptyComponent?: React.ReactNode;
  errorComponent?: React.ReactNode;
  navigationLoadingComponent?: React.ReactNode;
  placeholderDataComponent?: React.ReactNode;
}

export function CommonPanelLayout({
  children,
  title,
  count,
  headerChildren,
  footerChildren,
  isPlaceholderData = false,
  isNavigationLoading = false,
  isLoading = false,
  isError = false,
  isEmpty = false,
  error,
  onRetry,
  testId,
  skeletonComponent,
  emptyComponent,
  errorComponent,
  navigationLoadingComponent,
  placeholderDataComponent,
}: CommonPanelLayoutProps) {
  const t = useTranslations('jobResults');

  // Animation hook for smooth content transitions
  const { parentRef: contentRef } = useAutoAnimateList<HTMLDivElement>();
  
  return (
    <PanelSection data-testid={testId}>
      <PanelHeader
        title={title}
        count={count}
      >
        {headerChildren}
      </PanelHeader>
      
      {/* Placeholder data indicator */}
      {isPlaceholderData && placeholderDataComponent ? (
        placeholderDataComponent
      ) : isPlaceholderData ? (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 mb-4 text-sm text-blue-800">
          {t('loadingNewData')}
        </div>
      ) : null}
      
      <div ref={contentRef} className="space-y-4 relative">
        {isNavigationLoading && navigationLoadingComponent ? (
          navigationLoadingComponent
        ) : isNavigationLoading && !isEmpty ? (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-10 flex items-center justify-center rounded-lg">
            <div className="bg-background border rounded-lg px-4 py-2 shadow-sm flex items-center gap-2">
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-muted-foreground">{t('loading')}</span>
            </div>
          </div>
        ) : null}

        {isLoading && isEmpty && skeletonComponent ? (
          skeletonComponent
        ) : isLoading && isEmpty ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded-md animate-pulse"></div>
            ))}
          </div>
        ) : isError && errorComponent ? (
          errorComponent
        ) : isError ? (
          <div className="text-center py-8">
            <div className="text-red-500 mb-2">{t('errorLoadingData')}</div>
            <button
              onClick={onRetry}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              {t('retry')}
            </button>
            {error && <div className="text-sm text-muted-foreground mt-2">{error.message}</div>}
          </div>
        ) : isEmpty && emptyComponent ? (
          emptyComponent
        ) : isEmpty ? (
          <div className="text-center py-8 text-muted-foreground">
            {t('noItemsFound')}
          </div>
        ) : (
          children
        )}
      </div>
      
      {/* Footer children (e.g., feature phase toolbar) */}
      {footerChildren}
    </PanelSection>
  );
}
