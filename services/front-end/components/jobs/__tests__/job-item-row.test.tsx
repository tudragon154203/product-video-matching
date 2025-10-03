import React from 'react';
import { render, screen } from '@testing-library/react';
import { JobItemRow } from '../../jobs/JobItemRow';
import { useJobStatusPolling } from '@/lib/hooks/useJobStatusPolling';
import { getPhaseInfo } from '@/lib/api/utils/phase';
import { formatToGMT7 } from '@/lib/time';

// Mock external dependencies
jest.mock('@/lib/hooks/useJobStatusPolling');
jest.mock('@/lib/api/utils/phase');
jest.mock('@/lib/time');
jest.mock('next/link', () => {
  const Link = ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  );
  return Link;
});
jest.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant, className }: { children: React.ReactNode; variant?: string; className?: string }) => (
    <span className={`badge ${variant || ''} ${className || ''}`}>{children}</span>
  ),
}));

const mockUseJobStatusPolling = useJobStatusPolling as jest.MockedFunction<typeof useJobStatusPolling>;
const mockGetPhaseInfo = getPhaseInfo as jest.MockedFunction<typeof getPhaseInfo>;
const mockFormatToGMT7 = formatToGMT7 as jest.MockedFunction<typeof formatToGMT7>;

const mockJob = {
  job_id: 'test-job-id',
  query: 'test query',
  industry: 'test industry',
  phase: 'unknown', // This will be overridden by mockUseJobStatusPolling
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

describe('JobItemRow', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Default mock for useJobStatusPolling
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'unknown',
      percent: 0,
      counts: { products: 0, videos: 0, images: 0, frames: 0 },
      isCollecting: false,
    });

    // Default mock for getPhaseInfo
    mockGetPhaseInfo.mockImplementation((phase) => {
      switch (phase) {
        case 'unknown': return { label: 'Status unknown.', color: 'gray', effect: 'none' };
        case 'collection': return { label: 'Collecting products and videos…', color: 'blue', effect: 'animated-dots' };
        case 'feature_extraction': return { label: 'Extracting features (images / video frames)…', color: 'yellow', effect: 'progress-bar' };
        case 'matching': return { label: 'Matching products with videos…', color: 'purple', effect: 'spinner' };
        case 'evidence': return { label: 'Generating visual evidence…', color: 'orange', effect: 'progress-bar' };
        case 'completed': return { label: '✅ Completed!', color: 'green', effect: 'none' };
        case 'failed': return { label: '❌ Job failed.', color: 'red', effect: 'none' };
        default: return { label: '', color: '', effect: 'none' };
      }
    });

    // Default mock for formatToGMT7
    mockFormatToGMT7.mockReturnValue('2025-08-28 10:00 AM');
  });

  test('renders unknown phase correctly', () => {
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('Status unknown.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });

  test('renders collection phase with only phase label', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'collection',
      percent: 20,
      counts: { products: 1, videos: 1, images: 0, frames: 0 },
      isCollecting: true,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('Collecting products and videos…')).toBeInTheDocument();
    expect(screen.queryByTestId('status-color-circle')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-animated-dots')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-spinner')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-progress-bar')).not.toBeInTheDocument();
    expect(screen.queryByText('✔ Products done')).not.toBeInTheDocument();
    expect(screen.queryByText('✔ Videos done')).not.toBeInTheDocument();
    expect(screen.queryByText('Collection finished')).not.toBeInTheDocument();
  });

  test('renders feature_extraction phase with progress bar', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'feature_extraction',
      percent: 50,
      counts: { products: 1, videos: 1, images: 1, frames: 1 },
      isCollecting: false,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('Extracting features (images / video frames)…')).toBeInTheDocument();
    expect(screen.getByTestId('status-color-circle')).toHaveClass('bg-yellow-500');
    expect(screen.getByTestId('status-progress-bar')).toBeInTheDocument();
    expect(screen.queryByTestId('status-spinner')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-animated-dots')).not.toBeInTheDocument();
  });

  test('renders matching phase with spinner', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'matching',
      percent: 80,
      counts: { products: 1, videos: 1, images: 1, frames: 1 },
      isCollecting: false,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('Matching products with videos…')).toBeInTheDocument();
    expect(screen.getByTestId('status-color-circle')).toHaveClass('bg-purple-500');
    expect(screen.getByTestId('status-spinner')).toBeInTheDocument();
    expect(screen.queryByTestId('status-progress-bar')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-animated-dots')).not.toBeInTheDocument();
  });

  test('renders evidence phase with progress bar', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'evidence',
      percent: 90,
      counts: { products: 1, videos: 1, images: 1, frames: 1 },
      isCollecting: false,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('Generating visual evidence…')).toBeInTheDocument();
    expect(screen.getByTestId('status-color-circle')).toHaveClass('bg-orange-500');
    expect(screen.getByTestId('status-progress-bar')).toBeInTheDocument();
    expect(screen.queryByTestId('status-spinner')).not.toBeInTheDocument();
    expect(screen.queryByTestId('status-animated-dots')).not.toBeInTheDocument();
  });

  test('renders completed phase correctly', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'completed',
      percent: 100,
      counts: { products: 1, videos: 1, images: 1, frames: 1 },
      isCollecting: false,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('✅ Completed!')).toBeInTheDocument();
    expect(screen.getByTestId('status-color-circle')).toHaveClass('bg-green-500');
    expect(screen.queryByTestId('status-spinner')).not.toBeInTheDocument();
  });

  test('renders failed phase correctly', () => {
    mockUseJobStatusPolling.mockReturnValue({
      phase: 'failed',
      percent: 0,
      counts: { products: 0, videos: 0, images: 0, frames: 0 },
      isCollecting: false,
    });
    render(<JobItemRow job={mockJob} />);

    expect(screen.getByText('❌ Job failed.')).toBeInTheDocument();
    expect(screen.getByTestId('status-color-circle')).toHaveClass('bg-red-500');
    expect(screen.queryByTestId('status-spinner')).not.toBeInTheDocument();
  });

  test('aria-live attribute is present on the status container', () => {
    render(<JobItemRow job={mockJob} />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  });
});
