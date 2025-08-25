import { z } from 'zod';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

// Feature-related schemas
export const FeatureSummary = z.object({
  job_id: z.string(),
  total_product_images: z.number(),
  total_video_frames: z.number(),
  processed_product_images: z.number(),
  processed_video_frames: z.number(),
  feature_progress: z.object({
    segmentation: z.number(),
    embeddings: z.number(),
    keypoints: z.number(),
  }),
});

export const ProductImageFeature = z.object({
  img_id: z.string(),
  product_id: z.string(),
  local_path: z.string(),
  masked_local_path: z.string().nullable(),
  product_title: z.string(),
  has_segmentation: z.boolean(),
  has_embeddings: z.boolean(),
  has_keypoints: z.boolean(),
  updated_at: z.string(),
});

export const VideoFrameFeature = z.object({
  frame_id: z.string(),
  video_id: z.string(),
  ts: z.number(),
  local_path: z.string(),
  video_title: z.string(),
  has_segmentation: z.boolean(),
  has_embeddings: z.boolean(),
  has_keypoints: z.boolean(),
  updated_at: z.string(),
});

export const ProductImageFeaturesResponse = z.object({
  items: z.array(ProductImageFeature),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const VideoFrameFeaturesResponse = z.object({
  items: z.array(VideoFrameFeature),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

// Export types
export type FeatureSummary = z.infer<typeof FeatureSummary>;
export type ProductImageFeature = z.infer<typeof ProductImageFeature>;
export type VideoFrameFeature = z.infer<typeof VideoFrameFeature>;
export type ProductImageFeaturesResponse = z.infer<typeof ProductImageFeaturesResponse>;
export type VideoFrameFeaturesResponse = z.infer<typeof VideoFrameFeaturesResponse>;

/**
 * Feature API service for main-api feature endpoints
 */
export class FeatureApiService {
  /**
   * Get feature extraction summary for a job
   */
  async getFeatureSummary(jobId: string): Promise<FeatureSummary> {
    try {
      const response = await apiRequest<FeatureSummary>(mainApiClient, {
        method: 'GET',
        url: `/jobs/${jobId}/features/summary`,
      });
      
      return FeatureSummary.parse(response);
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
      limit?: number;
      offset?: number;
    }
  ): Promise<ProductImageFeaturesResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
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
      limit?: number;
      offset?: number;
    }
  ): Promise<VideoFrameFeaturesResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
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
  async getProductImageFeature(imgId: string): Promise<ProductImageFeature> {
    try {
      const response = await apiRequest<ProductImageFeature>(mainApiClient, {
        method: 'GET',
        url: `/features/product-images/${imgId}`,
      });
      
      return ProductImageFeature.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get individual video frame feature details
   */
  async getVideoFrameFeature(frameId: string): Promise<VideoFrameFeature> {
    try {
      const response = await apiRequest<VideoFrameFeature>(mainApiClient, {
        method: 'GET',
        url: `/features/video-frames/${frameId}`,
      });
      
      return VideoFrameFeature.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of FeatureApiService
 */
export const featureApiService = new FeatureApiService();