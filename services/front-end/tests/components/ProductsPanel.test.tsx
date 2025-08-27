import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProductsPanel } from '@/components/jobs/ProductsPanel/ProductsPanel';
import { usePanelData } from '@/components/CommonPanel/usePanelData';
import { productApiService } from '@/lib/api/services/product.api';
import { ProductItem } from '@/lib/zod/product';

// Mock the hook and API service
jest.mock('@/components/CommonPanel/usePanelData');
jest.mock('@/lib/api/services/product.api');

const mockUsePanelData = usePanelData as jest.MockedFunction<typeof usePanelData>;
const mockProductApiService = productApiService as jest.Mocked<typeof productApiService>;

// Mock ProductItem for testing
const mockProductItem: ProductItem = {
 product_id: 'test-product-1',
 title: 'Test Product',
 src: 'amazon.com',
 asin: 'B123456789',
 url: 'https://amazon.com/dp/B123456789',
 image_url: 'https://example.com/product.jpg',
 price: 29.99,
 price_currency: 'USD',
 description: 'Test product description',
 created_at: new Date().toISOString(),
 updated_at: new Date().toISOString(),
};

const mockProducts = Array.from({ length: 15 }, (_, i) => ({
 ...mockProductItem,
 product_id: `test-product-${i + 1}`,
 asin: `B12345678${i.toString().padStart(2, '0')}`,
}));

describe('ProductsPanel', () => {
 const mockJobId = 'test-job-123';

 beforeEach(() => {
   jest.clearAllMocks();
   
   // Setup mock hook response
   mockUsePanelData.mockReturnValue({
     items: mockProducts,
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   // Setup mock API service
   mockProductApiService.getJobProducts.mockResolvedValue({
     items: mockProducts,
     total: 15,
   });
 });

 test('should render panel with header and products', () => {
   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByTestId('products-panel')).toBeInTheDocument();
   expect(screen.getByText('15')).toBeInTheDocument(); // Total count
   
   // Should render product items
   expect(screen.getAllByText('Test Product')).toHaveLength(15);
   expect(screen.getByText('amazon.com')).toBeInTheDocument();
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByTestId('products-skeleton')).toBeInTheDocument();
 });

 test('should render empty state when no products', () => {
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByTestId('products-empty')).toBeInTheDocument();
 });

 test('should render error state when API call fails', () => {
   const errorMessage = 'Failed to fetch products';
   const mockHandleRetry = jest.fn();
   mockProductApiService.getJobProducts.mockRejectedValue(new Error(errorMessage));
   
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByTestId('products-error')).toBeInTheDocument();

   // Test retry functionality
   fireEvent.click(screen.getByTestId('products-retry'));
   expect(mockHandleRetry).toHaveBeenCalled();
 });

 test('should render navigation overlay when loading', () => {
   mockUsePanelData.mockReturnValue({
     items: mockProducts,
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   // Check for the loading spinner by its class name
   expect(screen.getByLabelText('Loading')).toBeInTheDocument();
   // Check for the loading text
   expect(screen.getByText('loading')).toBeInTheDocument();
 });

 test('should render placeholder data indicator', () => {
   mockUsePanelData.mockReturnValue({
     items: mockProducts,
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByText('🔄 Loading new data...')).toBeInTheDocument();
 });

 test('should render pagination when total > 10', () => {
   mockUsePanelData.mockReturnValue({
     items: mockProducts,
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.getByTestId('products-pagination')).toBeInTheDocument();
 });

 test('should not render pagination when total <= 10', () => {
   mockUsePanelData.mockReturnValue({
     items: mockProducts.slice(0, 5),
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   expect(screen.queryByTestId('products-pagination')).not.toBeInTheDocument();
 });

 test('should handle isCollecting prop correctly', () => {
   render(<ProductsPanel jobId={mockJobId} isCollecting={true} />);

   // The component should render with collecting state
   expect(screen.getByText('15')).toBeInTheDocument();
 });

 test('should group products by source', () => {
   mockUsePanelData.mockReturnValue({
     items: [
       { ...mockProductItem, src: 'amazon.com' },
       { ...mockProductItem, src: 'amazon.com', product_id: 'test-product-2' },
       { ...mockProductItem, src: 'ebay.com' },
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   render(<ProductsPanel jobId={mockJobId} />);

   // Should show group headers
   expect(screen.getByText('amazon.com')).toBeInTheDocument();
   expect(screen.getByText('ebay.com')).toBeInTheDocument();
 });

 test('should handle job ID change correctly', () => {
   const newJobId = 'test-job-456';

   const { rerender } = render(<ProductsPanel jobId={mockJobId} />);
   
   // Mock different data for the new job ID
   const newProducts = [{
     ...mockProductItem,
     product_id: 'new-product-1',
     src: 'new-source.com',
   }];

   mockUsePanelData.mockReturnValue({
     items: newProducts,
     total: 1,
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
     queryClient: {
       invalidateQueries: jest.fn(),
     },
     offset: 0,
     limit: 10,
   } as any);

   rerender(<ProductsPanel jobId={newJobId} />);

   expect(screen.getByText('new-source.com')).toBeInTheDocument();
 });
});