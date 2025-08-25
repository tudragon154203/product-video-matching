import { 
  VideoListResponse,
  FrameListResponse 
} from '@/lib/zod/video';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Video API service for main-api interactions
 */
export class VideoApiService {
  /**
   * Get videos for a specific job with filtering and pagination
   */
  async getJobVideos(
    jobId: string,
    params?: {
      q?: string;
      platform?: string;
      min_frames?: number;
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<VideoListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.q) {
        searchParams.append('q', params.q);
      }
      if (params?.platform) {
        searchParams.append('platform', params.platform);
      }
      if (params?.min_frames) {
        searchParams.append('min_frames', params.min_frames.toString());
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
      
      const url = `/jobs/${jobId}/videos${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<VideoListResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return VideoListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get frames for a specific video with pagination and sorting
   */
  async getVideoFrames(
    jobId: string,
    videoId: string,
    params?: {
      limit?: number;
      offset?: number;
      sort_by?: string;
      order?: string;
    }
  ): Promise<FrameListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
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
      
      const url = `/jobs/${jobId}/videos/${videoId}/frames${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<FrameListResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return FrameListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of VideoApiService
 */
export const videoApiService = new VideoApiService();