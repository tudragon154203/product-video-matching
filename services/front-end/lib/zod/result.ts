import { z } from 'zod';

/**
 * Product response schema (from main-api)
 */
export const ProductResponse = z.object({
  product_id: z.string(),
  src: z.string().nullable(),
  asin_or_itemid: z.string().nullable(),
  title: z.string().nullable(),
  brand: z.string().nullable(),
  url: z.string().nullable(),
  created_at: z.string(),
  image_count: z.number(),
});

/**
 * Video response schema (from main-api)
 */
export const VideoResponse = z.object({
  video_id: z.string(),
  platform: z.string().nullable(),
  url: z.string().nullable(),
  title: z.string().nullable(),
  duration_s: z.number().nullable(),
  published_at: z.string().nullable(),
  created_at: z.string(),
  frame_count: z.number(),
});

/**
 * Match response schema (from main-api)
 */
export const MatchResponse = z.object({
  match_id: z.string(),
  job_id: z.string(),
  product_id: z.string(),
  video_id: z.string(),
  best_img_id: z.string().nullable(),
  best_frame_id: z.string().nullable(),
  ts: z.number().nullable(),
  score: z.number(),
  evidence_path: z.string().nullable(),
  created_at: z.string(),
  // Enriched fields
  product_title: z.string().nullable(),
  video_title: z.string().nullable(),
  video_platform: z.string().nullable(),
});

/**
 * Match detail response schema (from main-api)
 */
export const MatchDetailResponse = z.object({
  match_id: z.string(),
  job_id: z.string(),
  best_img_id: z.string().nullable(),
  best_frame_id: z.string().nullable(),
  ts: z.number().nullable(),
  score: z.number(),
  evidence_path: z.string().nullable(),
  created_at: z.string(),
  product: ProductResponse,
  video: VideoResponse,
});

/**
 * Evidence response schema (from main-api)
 */
export const EvidenceResponse = z.object({
  evidence_path: z.string(),
});

/**
 * System statistics response schema (from main-api)
 */
export const StatsResponse = z.object({
  products: z.number(),
  product_images: z.number(),
  videos: z.number(),
  video_frames: z.number(),
  matches: z.number(),
  jobs: z.number(),
});

/**
 * Health response schema (from main-api)
 */
export const HealthResponse = z.object({
  status: z.string(),
  message: z.string().nullable(),
});

// Export types
export type ProductResponse = z.infer<typeof ProductResponse>;
export type VideoResponse = z.infer<typeof VideoResponse>;
export type MatchResponse = z.infer<typeof MatchResponse>;
export type MatchDetailResponse = z.infer<typeof MatchDetailResponse>;
export type EvidenceResponse = z.infer<typeof EvidenceResponse>;
export type StatsResponse = z.infer<typeof StatsResponse>;
export type HealthResponse = z.infer<typeof HealthResponse>;