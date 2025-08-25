import { z } from "zod";

export const ProductItem = z.object({
  product_id: z.string(),
  src: z.string(),
  asin_or_itemid: z.string(),
  title: z.string().nullable(),
  brand: z.string().nullable(),
  url: z.string().nullable(),
  image_count: z.number(),
  created_at: z.string(),
});

export const ProductListResponse = z.object({
  items: z.array(ProductItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export type ProductItem = z.infer<typeof ProductItem>;
export type ProductListResponse = z.infer<typeof ProductListResponse>;