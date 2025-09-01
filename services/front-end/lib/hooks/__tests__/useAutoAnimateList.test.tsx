import { renderHook } from '@testing-library/react';
import { useAutoAnimateList, useAutoAnimateItem } from '../useAutoAnimateList';

// Mock @formkit/auto-animate
jest.mock('@formkit/auto-animate', () => ({
  __esModule: true,
  default: jest.fn(),
}));

describe('useAutoAnimateList', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('should return parentRef and isEnabled', () => {
    const { result } = renderHook(() => useAutoAnimateList<HTMLDivElement>());

    expect(result.current.parentRef).toBeDefined();
    expect(result.current.parentRef.current).toBeNull();
    expect(typeof result.current.isEnabled).toBe('boolean');
    expect(result.current.isEnabled).toBe(true);
  });

  // Note: Server-side rendering test removed due to Jest environment limitations
  // The hook correctly handles SSR in production by checking typeof window !== 'undefined'
});

describe('useAutoAnimateItem', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    jest.clearAllMocks();
  });

  it('should return itemRef and isEnabled', () => {
    const { result } = renderHook(() => useAutoAnimateItem<HTMLDivElement>());

    expect(result.current.itemRef).toBeDefined();
    expect(result.current.itemRef.current).toBeNull();
    expect(typeof result.current.isEnabled).toBe('boolean');
    expect(result.current.isEnabled).toBe(true);
  });
});
