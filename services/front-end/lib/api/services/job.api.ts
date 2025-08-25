import { 
  JobStatus, 
  StartJobRequest, 
  StartJobResponse,
  JobListResponse 
} from '@/lib/zod/job';
import { mainApiClient, apiRequest } from '../client';
import { handleApiError } from '../utils/error-handling';

/**
 * Job API service for main-api interactions
 */
export class JobApiService {
  /**
   * Start a new matching job
   */
  async startJob(request: StartJobRequest): Promise<StartJobResponse> {
    try {
      const response = await apiRequest<StartJobResponse>(mainApiClient, {
        method: 'POST',
        url: '/start-job',
        data: request,
      });
      
      return StartJobResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Get status of a specific job
   */
  async getJobStatus(jobId: string): Promise<JobStatus> {
    try {
      const response = await apiRequest<JobStatus>(mainApiClient, {
        method: 'GET',
        url: `/status/${jobId}`,
      });
      
      return JobStatus.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * List jobs with pagination and filtering
   */
  async listJobs(params?: {
    limit?: number;
    offset?: number;
    status?: string;
  }): Promise<JobListResponse> {
    try {
      const searchParams = new URLSearchParams();
      
      if (params?.limit) {
        searchParams.append('limit', params.limit.toString());
      }
      if (params?.offset) {
        searchParams.append('offset', params.offset.toString());
      }
      if (params?.status) {
        searchParams.append('status', params.status);
      }
      
      const url = `/jobs${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
      
      const response = await apiRequest<JobListResponse>(mainApiClient, {
        method: 'GET',
        url,
      });
      
      return JobListResponse.parse(response);
    } catch (error) {
      throw handleApiError(error);
    }
  }

  /**
   * Health check for main-api service
   */
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await apiRequest<{ status: string; timestamp: string }>(mainApiClient, {
        method: 'GET',
        url: '/health',
      });
      
      return response;
    } catch (error) {
      throw handleApiError(error);
    }
  }
}

/**
 * Singleton instance of JobApiService
 */
export const jobApiService = new JobApiService();