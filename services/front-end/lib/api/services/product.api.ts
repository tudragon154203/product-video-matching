import { 
  ProductListResponse 
} from '@/lib/zod/product';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Product API service for main-api interactions
 */
export class ProductApiService {
  /**
   * Get products for a specific job with filtering and pagination
   */
  async getJobProducts(
    jobId: string,
    params?: {
      q?: string;
      src?: string;
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<ProductListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.q) {
        searchParams.append('q', params.q);
      }
      if (params?.src) {
        searchParams.append('src', params.src);
      }
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
      }
      if (params?.sort_by) {
        searchParams.append('sort_by', params.sort_by);
      }
      if (params?.order) {
        searchParams.append('order', params.order);
      }
      
      const url = `/jobs/${jobId}/products${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<ProductListResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return ProductListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of ProductApiService
 */
export const productApiService = new ProductApiService();