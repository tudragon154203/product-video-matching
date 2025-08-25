import { z } from 'zod';

/**
 * Match result schema
 */
export const MatchResult = z.object({
  match_id: z.string(),
  job_id: z.string(),
  product_id: z.string(),
  video_id: z.string(),
  best_img_id: z.string(),
  best_frame_id: z.string(),
  ts: z.number(),
  score: z.number(),
  evidence_path: z.string(),
  created_at: z.string(),
  product_title: z.string(),
  video_title: z.string(),
  video_platform: z.string(),
});

/**
 * Results list response schema
 */
export const ResultsListResponse = z.object({
  items: z.array(MatchResult),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

/**
 * Product detail schema
 */
export const ProductDetail = z.object({
  product_id: z.string(),
  src: z.string(),
  asin_or_itemid: z.string(),
  title: z.string(),
  brand: z.string(),
  url: z.string(),
  created_at: z.string(),
  image_count: z.number(),
});

/**
 * Video detail schema
 */
export const VideoDetail = z.object({
  video_id: z.string(),
  platform: z.string(),
  url: z.string(),
  title: z.string(),
  duration_s: z.number(),
  published_at: z.string(),
  created_at: z.string(),
  frame_count: z.number(),
});

/**
 * Match detail schema (includes product and video details)
 */
export const MatchDetail = z.object({
  match_id: z.string(),
  job_id: z.string(),
  product: ProductDetail,
  video: VideoDetail,
  best_img_id: z.string(),
  best_frame_id: z.string(),
  ts: z.number(),
  score: z.number(),
  evidence_path: z.string(),
  created_at: z.string(),
});

/**
 * System statistics schema
 */
export const SystemStats = z.object({
  products: z.number(),
  product_images: z.number(),
  videos: z.number(),
  video_frames: z.number(),
  matches: z.number(),
  jobs: z.number(),
});

/**
 * Health check response schema
 */
export const HealthResponse = z.object({
  status: z.string(),
  service: z.string(),
  timestamp: z.string(),
});

// Export types
export type MatchResult = z.infer<typeof MatchResult>;
export type ResultsListResponse = z.infer<typeof ResultsListResponse>;
export type ProductDetail = z.infer<typeof ProductDetail>;
export type VideoDetail = z.infer<typeof VideoDetail>;
export type MatchDetail = z.infer<typeof MatchDetail>;
export type SystemStats = z.infer<typeof SystemStats>;
export type HealthResponse = z.infer<typeof HealthResponse>;