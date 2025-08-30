import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NextIntlClientProvider } from 'next-intl';
import { ProductsPanel } from '@/components/jobs/ProductsPanel/ProductsPanel';
import { VideosPanel } from '@/components/jobs/VideosPanel/VideosPanel';
import * as imageApi from '@/lib/api/services/image.api';
import * as videoApi from '@/lib/api/services/video.api';
import * as productApi from '@/lib/api/services/product.api';

// Mock API services
jest.mock('@/lib/api/services/image.api');
jest.mock('@/lib/api/services/video.api');
jest.mock('@/lib/api/services/product.api');

// Mock Next.js Image component
jest.mock('next/image', () => ({
    __esModule: true,
    default: function MockImage(props: any) {
        return (
            <img
                {...props}
                data-testid=\"thumbnail-image\"
                    />
    );
  },
}));

// Mock common panel components to focus on thumbnail testing
jest.mock('@/components/CommonPanel', () => ({
    CommonPanelLayout: ({ children, skeletonComponent, isLoading }: any) => {
        if (isLoading) return skeletonComponent;
        return <div data-testid=\"panel-layout\">{children}</div>;
    },
    CommonPagination: () => <div data-testid=\"pagination\" />,
  usePanelData: jest.fn(),
}));

const mockImageApiService = imageApi.imageApiService as jest.Mocked<typeof imageApi.imageApiService>;
const mockVideoApiService = videoApi.videoApiService as jest.Mocked<typeof videoApi.videoApiService>;
const mockProductApiService = productApi.productApiService as jest.Mocked<typeof productApi.productApiService>;

const messages = {
    jobResults: {
        products: {
            panelTitle: 'Products',
            empty: 'No products found',
            collecting: 'Collecting products...',
        },
        videos: {
            panelTitle: 'Videos',
            empty: 'No videos found',
            collecting: 'Collecting videos...',
        },
    },
    errors: {
        loadFailed: 'Failed to load',
        retry: 'Retry',
    },
};

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });

    return (
        <QueryClientProvider client={queryClient}>
            <NextIntlClientProvider messages={messages} locale=\"en\">
            {children}
        </NextIntlClientProvider>
    </QueryClientProvider >
  );
};

describe('Thumbnail Integration Tests', () => {
    const mockJobId = 'test-job-123';

    beforeEach(() => {
        jest.clearAllMocks();
    });

    describe('ProductsPanel Thumbnails', () => {
        const mockProducts = [
            {
                product_id: 'prod-1',
                src: 'amazon',
                asin_or_itemid: 'B123456',
                title: 'Test Product 1',
                brand: 'TestBrand',
                url: 'https://amazon.com/product1',
                image_count: 3,
                created_at: '2024-01-01T00:00:00Z',
            },
            {
                product_id: 'prod-2',
                src: 'ebay',
                asin_or_itemid: 'E789012',
                title: 'Test Product 2',
                brand: null,
                url: 'https://ebay.com/product2',
                image_count: 1,
                created_at: '2024-01-02T00:00:00Z',
            },
        ];

        const mockImages = [
            {
                img_id: 'img-1',
                product_id: 'prod-1',
                local_path: '/app/data/images/img-1.jpg',
                url: 'http://localhost:8000/files/images/img-1.jpg',
                product_title: 'Test Product 1',
                updated_at: '2024-01-01T00:00:00Z',
            },
        ];

        beforeEach(() => {
            // Mock usePanelData to return products
            const { usePanelData } = require('@/components/CommonPanel');
            usePanelData.mockReturnValue({
                items: mockProducts,
                total: mockProducts.length,
                isLoading: false,
                isNavigationLoading: false,
                isError: false,
                error: null,
                handlePrev: jest.fn(),
                handleNext: jest.fn(),
                handleRetry: jest.fn(),
                isPlaceholderData: false,
                offset: 0,
                limit: 10,
            });

            // Mock image API to return first image for product
            mockImageApiService.getJobImages.mockResolvedValue({
                items: mockImages,
                total: 1,
                limit: 1,
                offset: 0,
            });
        });

        it('should display product thumbnails when images are available', async () => {
            render(
                <TestWrapper>
                    <ProductsPanel jobId={mockJobId} />
                </TestWrapper>
            );

            // Wait for products to render
            await waitFor(() => {
                expect(screen.getByText('Test Product 1')).toBeInTheDocument();
            });

            // Check if thumbnail images are present
            await waitFor(() => {
                const thumbnails = screen.getAllByTestId('product-thumbnail');
                expect(thumbnails).toHaveLength(mockProducts.length);
            });

            // Verify API was called to fetch images for first product
            expect(mockImageApiService.getJobImages).toHaveBeenCalledWith(
                mockJobId,
                {
                    product_id: 'prod-1',
                    limit: 1,
                    offset: 0,
                }
            );
        });

        it('should show placeholder when no images are available for product', async () => {
            // Mock empty images response
            mockImageApiService.getJobImages.mockResolvedValue({
                items: [],
                total: 0,
                limit: 1,
                offset: 0,
            });

            render(
                <TestWrapper>
                    <ProductsPanel jobId={mockJobId} />
                </TestWrapper>
            );

            await waitFor(() => {
                expect(screen.getByText('Test Product 1')).toBeInTheDocument();
            });

            // Should show placeholder icons
            await waitFor(() => {
                const placeholders = screen.getAllByTestId('thumbnail-placeholder-icon');
                expect(placeholders.length).toBeGreaterThan(0);
            });
        });
    });

    describe('VideosPanel Thumbnails', () => {
        const mockVideos = [
            {
                video_id: 'vid-1',
                platform: 'youtube',
                url: 'https://youtube.com/watch?v=123',
                title: 'Test Video 1',
                duration_s: 120,
                frames_count: 30,
                updated_at: '2024-01-01T00:00:00Z',
            },
            {
                video_id: 'vid-2',
                platform: 'tiktok',
                url: 'https://tiktok.com/@user/video/456',
                title: 'Test Video 2',
                duration_s: 60,
                frames_count: 15,
                updated_at: '2024-01-02T00:00:00Z',
            },
        ];

        const mockFrames = [
            {
                frame_id: 'frame-1',
                ts: 0.5,
                local_path: '/app/data/frames/frame-1.jpg',
                url: 'http://localhost:8000/files/frames/frame-1.jpg',
                updated_at: '2024-01-01T00:00:00Z',
            },
        ];

        beforeEach(() => {
            // Mock usePanelData to return videos
            const { usePanelData } = require('@/components/CommonPanel');
            usePanelData.mockReturnValue({
                items: mockVideos,
                total: mockVideos.length,
                isLoading: false,
                isNavigationLoading: false,
                isError: false,
                error: null,
                handlePrev: jest.fn(),
                handleNext: jest.fn(),
                handleRetry: jest.fn(),
                isPlaceholderData: false,
                offset: 0,
                limit: 10,
            });

            // Mock video frames API to return first frame
            mockVideoApiService.getVideoFrames.mockResolvedValue({
                items: mockFrames,
                total: 1,
                limit: 1,
                offset: 0,
            });
        });

        it('should display video thumbnails when frames are available', async () => {
            render(
                <TestWrapper>
                    <VideosPanel jobId={mockJobId} />
                </TestWrapper>
            );

            // Wait for videos to render
            await waitFor(() => {
                expect(screen.getByText('Test Video 1')).toBeInTheDocument();
            });

            // Check if thumbnail images are present
            await waitFor(() => {
                const thumbnails = screen.getAllByTestId('video-thumbnail');
                expect(thumbnails).toHaveLength(mockVideos.length);
            });

            // Verify API was called to fetch frames for first video
            expect(mockVideoApiService.getVideoFrames).toHaveBeenCalledWith(
                mockJobId,
                'vid-1',
                {
                    limit: 1,
                    offset: 0,
                    sort_by: 'ts',
                    order: 'ASC',
                }
            );
        });

        it('should show placeholder when no frames are available for video', async () => {
            // Mock empty frames response
            mockVideoApiService.getVideoFrames.mockResolvedValue({
                items: [],
                total: 0,
                limit: 1,
                offset: 0,
            });

            render(
                <TestWrapper>
                    <VideosPanel jobId={mockJobId} />
                </TestWrapper>
            );

            await waitFor(() => {
                expect(screen.getByText('Test Video 1')).toBeInTheDocument();
            });

            // Should show placeholder icons
            await waitFor(() => {
                const placeholders = screen.getAllByTestId('thumbnail-placeholder-icon');
                expect(placeholders.length).toBeGreaterThan(0);
            });
        });
    });

    describe('Thumbnail URL Formation', () => {
        it('should use url field from API response for product images', async () => {
            const mockProducts = [{
                product_id: 'prod-1',
                src: 'amazon',
                asin_or_itemid: 'B123456',
                title: 'Test Product',
                brand: 'TestBrand',
                url: 'https://amazon.com/product1',
                image_count: 1,
                created_at: '2024-01-01T00:00:00Z',
            }];

            const mockImages = [{
                img_id: 'img-1',
                product_id: 'prod-1',
                local_path: '/app/data/images/img-1.jpg',
                url: 'http://localhost:8000/files/images/img-1.jpg',
                product_title: 'Test Product',
                updated_at: '2024-01-01T00:00:00Z',
            }];

            const { usePanelData } = require('@/components/CommonPanel');
            usePanelData.mockReturnValue({
                items: mockProducts,
                total: 1,
                isLoading: false,
                isNavigationLoading: false,
                isError: false,
                error: null,
                handlePrev: jest.fn(),
                handleNext: jest.fn(),
                handleRetry: jest.fn(),
                isPlaceholderData: false,
                offset: 0,
                limit: 10,
            });

            mockImageApiService.getJobImages.mockResolvedValue({
                items: mockImages,
                total: 1,
                limit: 1,
                offset: 0,
            });

            render(
                <TestWrapper>
                    <ProductsPanel jobId={mockJobId} />
                </TestWrapper>
            );

            await waitFor(() => {
                const thumbnailImage = screen.getByTestId('thumbnail-image');
                expect(thumbnailImage).toHaveAttribute('src', 'http://localhost:8000/files/images/img-1.jpg');
            });
        });

        it('should use url field from API response for video frames', async () => {
            const mockVideos = [{
                video_id: 'vid-1',
                platform: 'youtube',
                url: 'https://youtube.com/watch?v=123',
                title: 'Test Video',
                duration_s: 120,
                frames_count: 30,
                updated_at: '2024-01-01T00:00:00Z',
            }];

            const mockFrames = [{
                frame_id: 'frame-1',
                ts: 0.5,
                local_path: '/app/data/frames/frame-1.jpg',
                url: 'http://localhost:8000/files/frames/frame-1.jpg',
                updated_at: '2024-01-01T00:00:00Z',
            }];

            const { usePanelData } = require('@/components/CommonPanel');
            usePanelData.mockReturnValue({
                items: mockVideos,
                total: 1,
                isLoading: false,
                isNavigationLoading: false,
                isError: false,
                error: null,
                handlePrev: jest.fn(),
                handleNext: jest.fn(),
                handleRetry: jest.fn(),
                isPlaceholderData: false,
                offset: 0,
                limit: 10,
            });

            mockVideoApiService.getVideoFrames.mockResolvedValue({
                items: mockFrames,
                total: 1,
                limit: 1,
                offset: 0,
            });

            render(
                <TestWrapper>
                    <VideosPanel jobId={mockJobId} />
                </TestWrapper>
            );

            await waitFor(() => {
                const thumbnailImage = screen.getByTestId('thumbnail-image');
                expect(thumbnailImage).toHaveAttribute('src', 'http://localhost:8000/files/frames/frame-1.jpg');
            });
        });
    });
});