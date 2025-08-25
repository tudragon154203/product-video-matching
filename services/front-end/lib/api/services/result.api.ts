import { 
  MatchResponse,
  ProductResponse,
  VideoResponse,
  MatchDetailResponse,
  EvidenceResponse,
  StatsResponse,
  HealthResponse,
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
  }): Promise<MatchResponse[]> {
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
      
      const response = await apiRequest<MatchResponse[]>(resultsApiClient, {
        method: 'GET',
        url,
      });
      
      return response.map(item => MatchResponse.parse(item));
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific product
   */
  async getProduct(productId: string): Promise<ProductResponse> {
    try {
      const response = await apiRequest<ProductResponse>(resultsApiClient, {
        method: 'GET',
        url: `/products/${productId}`,
      });
      
      return ProductResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific video
   */
  async getVideo(videoId: string): Promise<VideoResponse> {
    try {
      const response = await apiRequest<VideoResponse>(resultsApiClient, {
        method: 'GET',
        url: `/videos/${videoId}`,
      });
      
      return VideoResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get detailed information about a specific match
   */
  async getMatch(matchId: string): Promise<MatchDetailResponse> {
    try {
      const response = await apiRequest<MatchDetailResponse>(resultsApiClient, {
        method: 'GET',
        url: `/matches/${matchId}`,
      });
      
      return MatchDetailResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get evidence image path for a specific match
   */
  async getEvidence(matchId: string): Promise<EvidenceResponse> {
    try {
      const response = await apiRequest<EvidenceResponse>(resultsApiClient, {
        method: 'GET',
        url: `/evidence/${matchId}`,
      });
      
      return EvidenceResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get system statistics
   */
  async getStats(): Promise<StatsResponse> {
    try {
      const response = await apiRequest<StatsResponse>(resultsApiClient, {
        method: 'GET',
        url: '/stats',
      });
      
      return StatsResponse.parse(response);
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
}

/**
 * Singleton instance of ResultsApiService
 */
export const resultsApiService = new ResultsApiService();