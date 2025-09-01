'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ThumbnailImageProps {
    src?: string | null;
    alt: string;
    className?: string;
    'data-testid'?: string;
}

/**
 * ThumbnailImage component for displaying 120x120 thumbnails
 * Features:
 * - Fixed 120x120 size to prevent layout shift
 * - Lazy loading for performance
 * - Fallback placeholder on error or missing src
 * - Uses Next.js Image component for optimization
 */
export function ThumbnailImage({
    src,
    alt,
    className,
    'data-testid': dataTestId
}: ThumbnailImageProps) {
    const [hasError, setHasError] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Show placeholder if no src or error occurred
    const showPlaceholder = !src || hasError;

    const handleError = () => {
        setHasError(true);
        setIsLoading(false);
    };

    const handleLoad = () => {
        setIsLoading(false);
    };

    // Build absolute URL when API returns a relative path (e.g., "/files/images/..")
    let finalSrc = src || undefined;
    if (finalSrc && !/^https?:\/\//i.test(finalSrc)) {
        const base = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');
        if (finalSrc.startsWith('/')) {
            finalSrc = `${base}${finalSrc}`;
        }
        // else: leave as-is for data URIs or other schemes
    }

    return (
        <div
            className={cn(
                "relative w-[120px] h-[120px] rounded-md overflow-hidden bg-muted flex-shrink-0",
                className
            )}
            data-testid={dataTestId || 'thumbnail-image'}
        >
            {showPlaceholder ? (
                // Placeholder when no image or error
                <div className="w-full h-full flex items-center justify-center bg-muted">
                    <ImageIcon
                        className="w-8 h-8 text-muted-foreground"
                        data-testid="thumbnail-placeholder-icon"
                    />
                </div>
            ) : (
                <>
                    {/* Loading state */}
                    {isLoading && (
                        <div className="absolute inset-0 bg-muted animate-pulse flex items-center justify-center">
                            <ImageIcon
                                className="w-8 h-8 text-muted-foreground"
                                data-testid="thumbnail-loading-icon"
                            />
                        </div>
                    )}

                    {/* Actual image */}
                    <Image
                        src={finalSrc as string}
                        alt={alt || ""}
                        fill
                        className="object-cover"
                        loading="lazy"
                        onError={handleError}
                        onLoad={handleLoad}
                    />
                </>
            )}
        </div>
    );
}
