import { render, screen, waitFor, act, fireEvent } from '@testing-library/react';
import { useRouter } from 'next/navigation';
import { Providers } from '@/components/ui/providers';
import React, { useState } from 'react';
import { LoadingScreenProvider, useLoadingScreen } from '@/components/loading-screen';

// Mock the next/navigation useRouter to control route changes
let mockPathname = '/';
let mockSearchParams = new URLSearchParams();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    refresh: jest.fn(),
  }),
  usePathname: () => mockPathname,
  useSearchParams: () => mockSearchParams,
}));

// Mock next-intl useTranslations
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => {
    if (key === 'loading') return 'Loading...';
    return key;
  },
}));

// Mock performance.now() to work with fake timers
const MOCK_PERFORMANCE_NOW_OFFSET = 1000000; // Arbitrary large number to simulate real world performance.now() values
let mockPerformanceNow = MOCK_PERFORMANCE_NOW_OFFSET;

Object.defineProperty(global.performance, 'now', {
  value: jest.fn(() => mockPerformanceNow),
  writable: true,
});

// Test component that provides buttons to trigger startLoading and endLoading
// We need a separate component to use the hook inside the provider
const LoadingScreenControls: React.FC = () => {
  const { startLoading, endLoading } = useLoadingScreen();
  
  return (
    <>
      <button data-testid="start-loading" onClick={startLoading}>
        Start Loading
      </button>
      <button data-testid="end-loading" onClick={endLoading}>
        End Loading
      </button>
    </>
  );
};

const TestComponentWithControls: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  return (
    <Providers>
      <LoadingScreenProvider>
        <div data-testid="page-container">
          <LoadingScreenControls />
          {children}
        </div>
      </LoadingScreenProvider>
    </Providers>
  );
};

describe('Loading Screen Unit Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockPathname = '/'; // Reset pathname for each test
    mockSearchParams = new URLSearchParams(); // Reset searchParams for each test
    mockPerformanceNow = MOCK_PERFORMANCE_NOW_OFFSET; // Reset performance.now()
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  // UC-01: "Starts hidden" — on initial render, no loading state, no overlay.
  test('UC-01: Starts hidden - on initial render, no loading state, no overlay', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Initially, no loading overlay should be present
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Loading...')).not.toBeInTheDocument();
  });

  // UC-02: "Show on navigation start" — overlay visible after debounce period (150ms).
  test('UC-02: Show on navigation start - overlay visible after debounce', async () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Click start loading button
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Advance time by less than debounce time (149ms)
    act(() => {
      jest.advanceTimersByTime(149);
      mockPerformanceNow += 149;
    });
    
    // Overlay should not be visible yet
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    
    // Advance time to reach debounce time (1ms more)
    act(() => {
      jest.advanceTimersByTime(1);
      mockPerformanceNow += 1;
    });
    
    // Now overlay should be visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByLabelText('Loading...')).toBeInTheDocument();
  });

  // UC-03: "Hide on complete" — overlay hides respecting minimum visible time (300ms).
  test('UC-03: Hide on complete - overlay hides respecting minimum visible time', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Start loading
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Wait for overlay to appear (advance by debounce time)
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    
    // Verify overlay is visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // End loading immediately
    fireEvent.click(screen.getByTestId('end-loading'));
    
    // Advance time by less than min display time (299ms)
    act(() => {
      jest.advanceTimersByTime(299);
      mockPerformanceNow += 299;
    });
    
    // Overlay should still be visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // Advance time to exceed min display time (1ms more)
    act(() => {
      jest.advanceTimersByTime(1);
      mockPerformanceNow += 1;
    });
    
    // Advance timers further to ensure framer-motion exit animation completes
    act(() => {
      jest.advanceTimersByTime(200); // Additional time for animation
      mockPerformanceNow += 200;
    });
    
    // Overlay should now be hidden
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  // UC-04: "Hide on error" — overlay hides on navigation error (same as completion).
  test('UC-04: Hide on error - overlay hides on navigation error', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Start loading
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Wait for overlay to appear
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    
    // Verify overlay is visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // Simulate error by ending loading
    fireEvent.click(screen.getByTestId('end-loading'));
    
    // Advance time to exceed min display time
    act(() => {
      jest.advanceTimersByTime(300);
      mockPerformanceNow += 300;
    });
    
    // Advance timers further to ensure framer-motion exit animation completes
    act(() => {
      jest.advanceTimersByTime(200); // Additional time for animation
      mockPerformanceNow += 200;
    });
    
    // Overlay should be hidden
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  // UC-05: "Re-entrancy" — two quick navigations do not produce stacked overlays.
  test('UC-05: Re-entrancy - two quick navigations do not produce stacked overlays', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Start first loading
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Wait for first overlay to appear
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    
    // Verify overlay is visible
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // End first loading
    fireEvent.click(screen.getByTestId('end-loading'));
    
    // Start second loading quickly (before min display time of first)
    act(() => {
      jest.advanceTimersByTime(100); // Only 100ms passed since first start
      mockPerformanceNow += 100;
    });
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Advance time to exceed min display time of first + debounce of second
    act(() => {
      jest.advanceTimersByTime(200); // Total 300ms since first start, 200ms since second start
      mockPerformanceNow += 200;
    });
    
    // Overlay should still be visible (from second loading)
    expect(screen.getByRole('status')).toBeInTheDocument();
    
    // End second loading
    fireEvent.click(screen.getByTestId('end-loading'));
    
    // Advance time to exceed min display time of second
    act(() => {
      jest.advanceTimersByTime(300);
      mockPerformanceNow += 300;
    });
    
    // Advance timers further to ensure framer-motion exit animation completes
    act(() => {
      jest.advanceTimersByTime(200); // Additional time for animation
      mockPerformanceNow += 200;
    });
    
    // Overlay should be hidden
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  // UC-06: "A11y busy flag" — container toggles aria-busy and SR label exists.
  test('UC-06: A11y busy flag - container toggles aria-busy and SR label exists', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Get the main page container (this would be the one with aria-busy)
    // The page container is the div that wraps the children in the LoadingScreenProvider
    // We need to get the div that has the aria-busy attribute
    const pageContainer = screen.getByText('Page Content').closest('div[aria-busy]');
    
    // Initially, aria-busy should be false
    expect(pageContainer).toHaveAttribute('aria-busy', 'false');
    
    // Start loading
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Wait for overlay to appear
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    
    // aria-busy should be true when loading
    expect(pageContainer).toHaveAttribute('aria-busy', 'true');
    
    // End loading and wait for overlay to hide
    fireEvent.click(screen.getByTestId('end-loading'));
    act(() => {
      jest.advanceTimersByTime(300);
      mockPerformanceNow += 300;
    });
    
    // aria-busy should be false when not loading
    expect(pageContainer).toHaveAttribute('aria-busy', 'false');
    
    // Also verify the screen reader label exists when loading
    fireEvent.click(screen.getByTestId('start-loading'));
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    expect(screen.getByLabelText('Loading...')).toBeInTheDocument();
  });

  // UC-07: "Localization" — label pulls common.loading text from message bundle (EN/VI).
  test('UC-07: Localization - label pulls common.loading text (mocked)', () => {
    render(<TestComponentWithControls><div>Page Content</div></TestComponentWithControls>);
    
    // Start loading
    fireEvent.click(screen.getByTestId('start-loading'));
    
    // Wait for overlay to appear
    act(() => {
      jest.advanceTimersByTime(150);
      mockPerformanceNow += 150;
    });
    
    // Check for the loading text (will be "Loading..." due to our mock)
    expect(screen.getByLabelText('Loading...')).toBeInTheDocument();
  });
});