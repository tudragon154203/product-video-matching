import { 
  MatchResponse,
  ProductResponse,
  VideoResponse,
  MatchDetailResponse,
  EvidenceResponse,
  StatsResponse,
  HealthResponse,
} from '@/lib/zod/result';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';
import { MAIN_API_ENDPOINTS } from '../endpoints';

/**
 * Results API service for main-api results interactions
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
  }): Promise<{ items: MatchResponse[], total: number, limit: number, offset: number }> {
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
      
      const url = `${MAIN_API_ENDPOINTS.results}${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<{ items: MatchResponse[], total: number, limit: number, offset: number }>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return {
        ...response,
        items: response.items.map(item => MatchResponse.parse(item))
      };
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get matching results for a specific job
   */
  async getJobResults(
    jobId: string,
    params?: {
      industry?: string;
      min_score?: number;
      limit?: number;
      offset?: number;
    }
  ): Promise<{ items: MatchResponse[], total: number, limit: number, offset: number }> {
    return this.getResults({
      ...params,
      job_id: jobId,
    });
  }

  /**
   * Get detailed information about a specific product
   * Note: Product details are now included in match detail responses
   * This method is deprecated - use getMatch() instead for full product context
   * @deprecated Use getMatch() to get product details within match context
   */
  async getProduct(productId: string): Promise<ProductResponse> {
    throw new Error('Product detail endpoint has been consolidated into match details. Use getMatch() instead.');
  }

  /**
   * Get detailed information about a specific video
   * Note: Video details are now included in match detail responses
   * This method is deprecated - use getMatch() instead for full video context
   * @deprecated Use getMatch() to get video details within match context
   */
  async getVideo(videoId: string): Promise<VideoResponse> {
    throw new Error('Video detail endpoint has been consolidated into match details. Use getMatch() instead.');
  }

  /**
   * Get detailed information about a specific match
   */
  async getMatch(matchId: string): Promise<MatchDetailResponse> {
    try {
      const response = await apiRequest<MatchDetailResponse>(mainApiClient, {
        method: 'GET',
        url: MAIN_API_ENDPOINTS.matches.detail(matchId),
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
      const response = await apiRequest<EvidenceResponse>(mainApiClient, {
        method: 'GET',
        url: MAIN_API_ENDPOINTS.evidence(matchId),
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
      const response = await apiRequest<StatsResponse>(mainApiClient, {
        method: 'GET',
        url: MAIN_API_ENDPOINTS.stats,
      });
      
      return StatsResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Health check for main-api service
   */
  async healthCheck(): Promise<HealthResponse> {
    try {
      const response = await apiRequest<HealthResponse>(mainApiClient, {
        method: 'GET',
        url: MAIN_API_ENDPOINTS.health,
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