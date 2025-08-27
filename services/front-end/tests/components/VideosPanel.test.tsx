import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { VideosPanel } from '@/components/jobs/VideosPanel/VideosPanel';
import { usePanelData } from '@/components/CommonPanel/usePanelData';
import { videoApiService } from '@/lib/api/services/video.api';
import { VideoItem } from '@/lib/zod/video';

// Mock the hook and API service
jest.mock('@/components/CommonPanel/usePanelData');
jest.mock('@/lib/api/services/video.api');

const mockUsePanelData = usePanelData as jest.MockedFunction<typeof usePanelData>;
const mockVideoApiService = videoApiService as jest.Mocked<typeof videoApiService>;

// Mock VideoItem for testing
const mockVideoItem: VideoItem = {
  video_id: 'test-video-1',
  platform: 'youtube',
  url: 'https://youtube.com/watch?v=test123',
  title: 'Test Video',
  duration_s: 120,
  frames_count: 10,
  updated_at: new Date().toISOString(),
};

const mockVideos = Array.from({ length: 15 }, (_, i) => ({
  ...mockVideoItem,
  video_id: `test-video-${i + 1}`,
}));

describe('VideosPanel', () => {
  const mockJobId = 'test-job-123';

  beforeEach(() => {
    jest.clearAllMocks();
    
    // Setup mock hook response
    mockUsePanelData.mockReturnValue({
      items: mockVideos,
      total: 15,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    // Setup mock API service
    mockVideoApiService.getJobVideos.mockResolvedValue({
      items: mockVideos,
      total: 15,
    } as any);
  });

  test('should render panel with header and videos', () => {
    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByTestId('videos-panel')).toBeInTheDocument();
    expect(screen.getByText('Videos')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument(); // Total count
    
    // Should render video items
    expect(screen.getAllByText('Test Video')).toHaveLength(15);
    expect(screen.getByText('YouTube')).toBeInTheDocument();
  });

  test('should render skeleton when loading', () => {
    mockUsePanelData.mockReturnValue({
      items: [],
      total: 0,
      isLoading: true,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: true,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByTestId('videos-skeleton')).toBeInTheDocument();
  });

  test('should render empty state when no videos', () => {
    mockUsePanelData.mockReturnValue({
      items: [],
      total: 0,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByTestId('videos-empty')).toBeInTheDocument();
  });

  test('should render error state when API call fails', () => {
    const errorMessage = 'Failed to fetch videos';
    const mockHandleRetry = jest.fn();
    mockVideoApiService.getJobVideos.mockRejectedValue(new Error(errorMessage));
    
    mockUsePanelData.mockReturnValue({
      items: [],
      total: 0,
      isLoading: false,
      isNavigationLoading: false,
      isError: true,
      error: new Error(errorMessage),
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: mockHandleRetry,
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByTestId('videos-error')).toBeInTheDocument();

    // Test retry functionality
    fireEvent.click(screen.getByText('Retry'));
    expect(mockHandleRetry).toHaveBeenCalled();
  });

  test('should render navigation overlay when loading', () => {
    mockUsePanelData.mockReturnValue({
      items: mockVideos,
      total: 15,
      isLoading: false,
      isNavigationLoading: true,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByText('Loading')).toBeInTheDocument();
  });

  test('should render placeholder data indicator', () => {
    mockUsePanelData.mockReturnValue({
      items: mockVideos,
      total: 15,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: true,
      isPlaceholderData: true,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByText('🔄 Loading new data...')).toBeInTheDocument();
  });

  test('should render pagination when total > 10', () => {
    mockUsePanelData.mockReturnValue({
      items: mockVideos,
      total: 15,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.getByTestId('videos-pagination')).toBeInTheDocument();
  });

  test('should not render pagination when total <= 10', () => {
    mockUsePanelData.mockReturnValue({
      items: mockVideos.slice(0, 5),
      total: 5,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    expect(screen.queryByTestId('videos-pagination')).not.toBeInTheDocument();
  });

  test('should handle isCollecting prop correctly', () => {
    render(<VideosPanel jobId={mockJobId} isCollecting={true} />);

    // The component should render with collecting state
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  test('should group videos by platform', () => {
    mockUsePanelData.mockReturnValue({
      items: [
        { ...mockVideoItem, platform: 'youtube' },
        { ...mockVideoItem, platform: 'youtube', video_id: 'test-video-2' },
        { ...mockVideoItem, platform: 'tiktok' },
      ],
      total: 3,
      isLoading: false,
      isNavigationLoading: false,
      isError: false,
      error: null,
      isFetching: false,
      isPlaceholderData: false,
      handlePrev: jest.fn(),
      handleNext: jest.fn(),
      handleRetry: jest.fn(),
      refetch: jest.fn(),
      queryClient: {} as any,
      offset: 0,
      limit: 10,
    } as any);

    render(<VideosPanel jobId={mockJobId} />);

    // Should show group headers
    expect(screen.getByText('YouTube')).toBeInTheDocument();
    expect(screen.getByText('TikTok')).toBeInTheDocument();
  });
});