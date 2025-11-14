'use client';

import React, { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { ChevronDown, ChevronUp, Package, Video, CheckCircle2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface CollectionSummaryProps {
  phase: string;
  collection?: {
    products_done: boolean;
    videos_done: boolean;
  };
  counts: {
    products: number;
    videos: number;
    images: number;
    frames: number;
  };
  updatedAt?: string;
  children?: React.ReactNode; // The Products/Videos panels
}

export function CollectionSummary({ 
  phase, 
  collection, 
  counts,
  updatedAt,
  children 
}: CollectionSummaryProps) {
  const t = useTranslations();
  
  // Auto-collapse when entering feature_extraction phase
  const shouldCollapse = phase === 'feature_extraction' || phase === 'matching' || phase === 'evidence';
  
  // Remember user preference per session
  const [isExpanded, setIsExpanded] = useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = sessionStorage.getItem('collectionSummaryExpanded');
    return stored !== null ? stored === 'true' : false;
  });

  // Auto-collapse when phase changes to feature_extraction
  useEffect(() => {
    if (shouldCollapse && isExpanded) {
      setIsExpanded(false);
    }
  }, [shouldCollapse]);

  // Save preference to session storage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('collectionSummaryExpanded', String(isExpanded));
    }
  }, [isExpanded]);

  // Don't show during collection phase (it's the current phase)
  if (phase === 'collection') {
    return null;
  }

  // Don't show if no collection data
  if (!collection) {
    return null;
  }

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
      return new Date(dateStr).toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Accordion Header - shows summary when collapsed */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors"
        aria-expanded={isExpanded}
        aria-controls="collection-summary-content"
      >
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4 text-slate-600" />
              ) : (
                <ChevronDown className="h-4 w-4 text-slate-600" />
              )}
              <h3 className="font-semibold text-sm">Collection Summary</h3>
            </div>
            
            {/* Show badges when collapsed */}
            {!isExpanded && (
              <div className="flex items-center gap-2">
                {collection.products_done && (
                  <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Products
                  </Badge>
                )}
                {collection.videos_done && (
                  <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Videos
                  </Badge>
                )}
              </div>
            )}
          </div>

          {/* Show counts when collapsed */}
          {!isExpanded && (
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Package className="h-3 w-3" />
                <span>Products: {counts.products}</span>
              </div>
              <div className="flex items-center gap-1">
                <span>Images: {counts.images}</span>
              </div>
              <div className="flex items-center gap-1">
                <Video className="h-3 w-3" />
                <span>Videos: {counts.videos}</span>
              </div>
              <div className="flex items-center gap-1">
                <span>Frames: {counts.frames}</span>
              </div>
            </div>
          )}
        </div>
      </button>

      {/* Accordion Content - shows the actual panels when expanded */}
      {isExpanded && (
        <div 
          id="collection-summary-content"
          className="bg-white"
        >
          {children}
        </div>
      )}
    </div>
  );
}
