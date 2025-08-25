import { 
  ImageListResponse 
} from '@/lib/zod/image';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Image API service for main-api interactions
 */
export class ImageApiService {
  /**
   * Get images for a specific job with filtering and pagination
   */
  async getJobImages(
    jobId: string,
    params?: {
      product_id?: string;
      q?: string;
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<ImageListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.product_id) {
        searchParams.append('product_id', params.product_id);
      }
      if (params?.q) {
        searchParams.append('q', params.q);
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
      
      const url = `/jobs/${jobId}/images${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<ImageListResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return ImageListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of ImageApiService
 */
export const imageApiService = new ImageApiService();