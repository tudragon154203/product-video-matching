import { mainApiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import { MatchingSummaryResponse } from '@/lib/zod/matching';

export const matchingApiService = {
  /**
   * Get matching phase summary for a job
   */
  getMatchingSummary: async (
    jobId: string,
    forceRefresh = false
  ): Promise<MatchingSummaryResponse> => {
    const params = forceRefresh ? { force_refresh: 'true' } : {};
    const response = await mainApiClient.get(
      API_ENDPOINTS.main.matching.summary(jobId),
      { params }
    );
    return MatchingSummaryResponse.parse(response.data);
  },
};
