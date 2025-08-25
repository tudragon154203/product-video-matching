import { 
  FeaturesSummaryResponse,
  ProductImageFeaturesResponse,
  VideoFrameFeaturesResponse,
  ProductImageFeatureItem,
  VideoFrameFeatureItem
} from '@/lib/zod/features';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Feature API service for main-api feature endpoints
 */
export class FeatureApiService {
  /**
   * Get feature extraction summary for a job
   */
  async getFeatureSummary(jobId: string): Promise<FeaturesSummaryResponse> {
    try {
      const response = await apiRequest<FeaturesSummaryResponse>(mainApiClient, {
        method: 'GET',
        url: `/jobs/${jobId}/features/summary`,
      });
      
      return FeaturesSummaryResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get product images with feature status
   */
  async getProductImageFeatures(
    jobId: string,
    params?: {
      has?: string;
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<ProductImageFeaturesResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.has) {
        searchParams.append('has', params.has);
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
      
      const url = `/jobs/${jobId}/features/product-images${
        searchParams.toString() ? `?${searchParams.toString()}` : ''
      }`;
      
      const response = await apiRequest<ProductImageFeaturesResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return ProductImageFeaturesResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get video frames with feature status
   */
  async getVideoFrameFeatures(
    jobId: string,
    params?: {
      video_id?: string;
      has?: string;
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<VideoFrameFeaturesResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.video_id) {
        searchParams.append('video_id', params.video_id);
      }
      if (params?.has) {
        searchParams.append('has', params.has);
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
      
      const url = `/jobs/${jobId}/features/video-frames${
        searchParams.toString() ? `?${searchParams.toString()}` : ''
      }`;
      
      const response = await apiRequest<VideoFrameFeaturesResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return VideoFrameFeaturesResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get individual product image feature details
   */
  async getProductImageFeature(imgId: string): Promise<ProductImageFeatureItem> {
    try {
      const response = await apiRequest<ProductImageFeatureItem>(mainApiClient, {
        method: 'GET',
        url: `/features/product-images/${imgId}`,
      });
      
      return ProductImageFeatureItem.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get individual video frame feature details
   */
  async getVideoFrameFeature(frameId: string): Promise<VideoFrameFeatureItem> {
    try {
      const response = await apiRequest<VideoFrameFeatureItem>(mainApiClient, {
        method: 'GET',
        url: `/features/video-frames/${frameId}`,
      });
      
      return VideoFrameFeatureItem.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of FeatureApiService
 */
export const featureApiService = new FeatureApiService();