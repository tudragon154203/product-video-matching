import { z } from "zod";

/**
 * Video item schema for main-api video endpoints
 */
export const VideoItem = z.object({
  video_id: z.string(),
  platform: z.string(),
  url: z.string(),
  title: z.string(),
  duration_s: z.number(),
  frames_count: z.number(),
  updated_at: z.string(),
});

/**
 * Video list response schema with pagination
 */
export const VideoListResponse = z.object({
  items: z.array(VideoItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

/**
 * Frame item schema for video frames
 */
export const FrameItem = z.object({
  frame_id: z.string(),
  ts: z.number(),
  local_path: z.string(),
  updated_at: z.string(),
});

/**
 * Frame list response schema with pagination
 */
export const FrameListResponse = z.object({
  items: z.array(FrameItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

// Export types
export type VideoItem = z.infer<typeof VideoItem>;
export type VideoListResponse = z.infer<typeof VideoListResponse>;
export type FrameItem = z.infer<typeof FrameItem>;
export type FrameListResponse = z.infer<typeof FrameListResponse>;