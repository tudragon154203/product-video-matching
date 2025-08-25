import { 
  ResultsListResponse,
  ProductDetail,
  VideoDetail,
  MatchDetail,
  SystemStats,
  HealthResponse,
  PaginatedProductListResponse,
  PaginatedVideoListResponse,
  JobStatusResponse,
} from '@/lib/zod/result';
import { resultsApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Results API service for results-api interactions
 */
export class ResultsApiService {
  /**
   * Get matching results with filtering and pagination
   */
  async getResults(params?: {
    industry?: string;
    min_score?: number;
    job_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<ResultsListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.industry) {
        searchParams.append('industry', params.industry);
      }
      if (params?.min_score !== undefined) {
        searchParams.append('min_score', params.min_score.toString());
      }
      if (params?.job_id) {
        searchParams.append('job_id', params.job_id);
      }
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
      }
      
      const url = `/results${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<ResultsListResponse>(resultsApiClient, {
        method: 'GET',
        url,
      });
      
      return ResultsListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific product
   */
  async getProduct(productId: string): Promise<ProductDetail> {
    try {
      const response = await apiRequest<ProductDetail>(resultsApiClient, {
        method: 'GET',
        url: `/products/${productId}`,
      });
      
      return ProductDetail.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific video
   */
  async getVideo(videoId: string): Promise<VideoDetail> {
    try {
      const response = await apiRequest<VideoDetail>(resultsApiClient, {
        method: 'GET',
        url: `/videos/${videoId}`,
      });
      
      return VideoDetail.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific match
   */
  async getMatch(matchId: string): Promise<MatchDetail> {
    try {
      const response = await apiRequest<MatchDetail>(resultsApiClient, {
        method: 'GET',
        url: `/matches/${matchId}`,
      });
      
      return MatchDetail.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get evidence image for a specific match
   */
  async getEvidence(matchId: string): Promise<Blob> {
    try {
      const response = await resultsApiClient.get(`/evidence/${matchId}`, {
        responseType: 'blob',
      });
      
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get system statistics
   */
  async getStats(): Promise<SystemStats> {
    try {
      const response = await apiRequest<SystemStats>(resultsApiClient, {
        method: 'GET',
        url: '/stats',
      });
      
      return SystemStats.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Health check for results-api service
   */
  async healthCheck(): Promise<HealthResponse> {
    try {
      const response = await apiRequest<HealthResponse>(resultsApiClient, {
        method: 'GET',
        url: '/health',
      });
      
      return HealthResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get paginated list of products for a specific job
   */
  async getJobProducts(jobId: string, params?: {
    limit?: number;
    offset?: number;
  }): Promise<PaginatedProductListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
      }
      
      const url = `/jobs/${jobId}/products${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<PaginatedProductListResponse>(resultsApiClient, {
        method: 'GET',
        url,
      });
      
      return PaginatedProductListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get paginated list of videos for a specific job
   */
  async getJobVideos(jobId: string, params?: {
    limit?: number;
    offset?: number;
  }): Promise<PaginatedVideoListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
      }
      
      const url = `/jobs/${jobId}/videos${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<PaginatedVideoListResponse>(resultsApiClient, {
        method: 'GET',
        url,
      });
      
      return PaginatedVideoListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get status for a specific job
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    try {
      const url = `/status/${jobId}`;
      
      const response = await apiRequest<JobStatusResponse>(resultsApiClient, {
        method: 'GET',
        url,
      });
      
      return JobStatusResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of ResultsApiService
 */
export const resultsApiService = new ResultsApiService();