import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  jobApiService,
  productApiService,
  videoApiService,
  imageApiService,
  featureApiService,
  resultsApiService
} from './services';
import { getPollingInterval } from '@/lib/config/pagination';
import type {
  StartJobRequest,
  JobStatus,
  JobListResponse,
  ProductListResponse,
  VideoListResponse,
  FrameListResponse,
  ImageListResponse,
  FeaturesSummaryResponse,
  ProductImageFeaturesResponse,
  VideoFrameFeaturesResponse,
  CancelJobRequest,
} from '@/lib/zod';

/**
 * Query keys for React Query
 */
export const queryKeys = {
  jobs: {
    all: ['jobs'] as const,
    list: (params?: any) => ['jobs', 'list', params] as const,
    status: (jobId: string) => ['jobs', 'status', jobId] as const,
  },
  products: {
    all: ['products'] as const,
    byJob: (jobId: string, params?: any) => ['products', 'job', jobId, params] as const,
  },
  videos: {
    all: ['videos'] as const,
    byJob: (jobId: string, params?: any) => ['videos', 'job', jobId, params] as const,
    frames: (jobId: string, videoId: string, params?: any) => ['videos', 'frames', jobId, videoId, params] as const,
  },
  images: {
    all: ['images'] as const,
    byJob: (jobId: string, params?: any) => ['images', 'job', jobId, params] as const,
  },
  features: {
    all: ['features'] as const,
    summary: (jobId: string) => ['features', 'summary', jobId] as const,
    productImages: (jobId: string, params?: any) => ['features', 'product-images', jobId, params] as const,
    videoFrames: (jobId: string, params?: any) => ['features', 'video-frames', jobId, params] as const,
    productImage: (imgId: string) => ['features', 'product-image', imgId] as const,
    videoFrame: (frameId: string) => ['features', 'video-frame', frameId] as const,
  },
  results: {
    all: ['results'] as const,
    matches: (jobId: string, params?: any) => ['results', 'matches', jobId, params] as const,
    matchDetail: (matchId: string) => ['results', 'match', matchId] as const,
  },
} as const;

// Job hooks
export const useStartJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: StartJobRequest) => jobApiService.startJob(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
    },
  });
};

export const useCancelJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ jobId, request }: { jobId: string; request?: CancelJobRequest }) =>
      jobApiService.cancelJob(jobId, request),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.status(data.job_id) });
    },
  });
};

export const useDeleteJob = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ jobId, force }: { jobId: string; force?: boolean }) =>
      jobApiService.deleteJob(jobId, force),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.jobs.all });
      queryClient.removeQueries({ queryKey: queryKeys.jobs.status(data.job_id) });
    },
  });
};

export const useJobStatus = (jobId: string, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.jobs.status(jobId),
    queryFn: () => jobApiService.getJobStatus(jobId),
    enabled: enabled && !!jobId,
    refetchInterval: getPollingInterval('jobStatus'), // Use centralized config
  });
};

export const useJobList = (params?: { limit?: number; offset?: number; status?: string }) => {
  return useQuery({
    queryKey: queryKeys.jobs.list(params),
    queryFn: () => jobApiService.listJobs(params),
  });
};

// Product hooks
export const useJobProducts = (
  jobId: string,
  params?: {
    q?: string;
    src?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.products.byJob(jobId, params),
    queryFn: () => productApiService.getJobProducts(jobId, params),
    enabled: enabled && !!jobId,
  });
};

// Video hooks
export const useJobVideos = (
  jobId: string,
  params?: {
    q?: string;
    platform?: string;
    min_frames?: number;
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.videos.byJob(jobId, params),
    queryFn: () => videoApiService.getJobVideos(jobId, params),
    enabled: enabled && !!jobId,
  });
};

export const useVideoFrames = (
  jobId: string,
  videoId: string,
  params?: {
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.videos.frames(jobId, videoId, params),
    queryFn: () => videoApiService.getVideoFrames(jobId, videoId, params),
    enabled: enabled && !!jobId && !!videoId,
  });
};

// Image hooks
export const useJobImages = (
  jobId: string,
  params?: {
    product_id?: string;
    q?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.images.byJob(jobId, params),
    queryFn: () => imageApiService.getJobImages(jobId, params),
    enabled: enabled && !!jobId,
  });
};

// Feature hooks
export const useFeaturesSummary = (jobId: string, enabled = true, refetchInterval?: number | false) => {
  return useQuery({
    queryKey: queryKeys.features.summary(jobId),
    queryFn: () => featureApiService.getFeatureSummary(jobId),
    enabled: enabled && !!jobId,
    refetchInterval: refetchInterval !== undefined ? refetchInterval : false,
    staleTime: 0,
  });
};

export const useProductImageFeatures = (
  jobId: string,
  params?: {
    has?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.features.productImages(jobId, params),
    queryFn: () => featureApiService.getProductImageFeatures(jobId, params),
    enabled: enabled && !!jobId,
  });
};

export const useVideoFrameFeatures = (
  jobId: string,
  params?: {
    video_id?: string;
    has?: string;
    limit?: number;
    offset?: number;
    sort_by?: string;
    order?: string;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.features.videoFrames(jobId, params),
    queryFn: () => featureApiService.getVideoFrameFeatures(jobId, params),
    enabled: enabled && !!jobId,
  });
};

export const useProductImageFeature = (imgId: string, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.features.productImage(imgId),
    queryFn: () => featureApiService.getProductImageFeature(imgId),
    enabled: enabled && !!imgId,
  });
};

export const useVideoFrameFeature = (frameId: string, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.features.videoFrame(frameId),
    queryFn: () => featureApiService.getVideoFrameFeature(frameId),
    enabled: enabled && !!frameId,
  });
};

// Results/Matches hooks
export const useJobMatches = (
  jobId: string,
  params?: {
    industry?: string;
    min_score?: number;
    limit?: number;
    offset?: number;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: queryKeys.results.matches(jobId, params),
    queryFn: () => resultsApiService.getJobResults(jobId, params),
    enabled: enabled && !!jobId,
  });
};

export const useMatchDetail = (matchId: string, enabled = true) => {
  return useQuery({
    queryKey: queryKeys.results.matchDetail(matchId),
    queryFn: () => resultsApiService.getMatch(matchId),
    enabled: enabled && !!matchId,
  });
};

export const useResults = (
  params?: {
    industry?: string;
    min_score?: number;
    job_id?: string;
    limit?: number;
    offset?: number;
  },
  enabled = true
) => {
  return useQuery({
    queryKey: ['results', 'all', params],
    queryFn: () => resultsApiService.getResults(params),
    enabled,
  });
};