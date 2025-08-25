# Zod Schema Suite for Main API

This directory contains comprehensive Zod schemas for all main-api endpoints, providing type-safe validation and TypeScript types for the frontend application.

## Structure

### Core Schema Files

- **`common.ts`** - Common schemas for pagination, sorting, filtering, and search parameters
- **`job.ts`** - Job-related schemas (start job, job status, job listing)
- **`product.ts`** - Product-related schemas (product items and listings)
- **`video.ts`** - Video-related schemas (video items, frames, and listings)
- **`image.ts`** - Image-related schemas (image items and listings)
- **`features.ts`** - Feature extraction schemas (summaries, progress, feature items)
- **`result.ts`** - Results API schemas (matches, evidence, statistics)

### Main API Endpoints Covered

#### Job Management
- `POST /start-job` - Start a new matching job
- `GET /status/{job_id}` - Get job status and progress
- `GET /jobs` - List jobs with pagination and filtering

#### Product Data
- `GET /jobs/{job_id}/products` - Get products for a job with filtering

#### Video Data
- `GET /jobs/{job_id}/videos` - Get videos for a job with filtering
- `GET /jobs/{job_id}/videos/{video_id}/frames` - Get frames for a video

#### Image Data
- `GET /jobs/{job_id}/images` - Get images for a job with filtering

#### Feature Extraction
- `GET /jobs/{job_id}/features/summary` - Get feature extraction summary
- `GET /jobs/{job_id}/features/product-images` - Get product image features
- `GET /jobs/{job_id}/features/video-frames` - Get video frame features
- `GET /features/product-images/{img_id}` - Get individual product image features
- `GET /features/video-frames/{frame_id}` - Get individual video frame features

## Usage

### Import Schemas
```typescript
import { 
  StartJobRequest, 
  JobStatus, 
  ProductListResponse,
  VideoListResponse,
  FeaturesSummaryResponse 
} from '@/lib/zod';
```

### Validate API Responses
```typescript
import { JobStatus } from '@/lib/zod/job';

const response = await fetch('/api/status/job123');
const data = await response.json();
const validatedData = JobStatus.parse(data);
```

### Use with API Services
```typescript
import { jobApiService } from '@/lib/api/services';

const jobStatus = await jobApiService.getJobStatus('job123');
// jobStatus is automatically typed and validated
```

## Type Safety

All schemas provide corresponding TypeScript types:

```typescript
import type { 
  StartJobRequest, 
  JobStatus, 
  ProductItem,
  VideoItem,
  FeatureProgress 
} from '@/lib/zod';
```

## Validation Features

- **Runtime validation** - All API responses are validated at runtime
- **Type inference** - TypeScript types are automatically inferred from schemas
- **Error handling** - Detailed validation errors for debugging
- **Optional fields** - Proper handling of nullable and optional fields
- **Enums** - Strict validation of enumerated values (phases, platforms, etc.)

## Common Patterns

### Pagination
All list endpoints use consistent pagination:
```typescript
{
  items: T[],
  total: number,
  limit: number,
  offset: number
}
```

### Filtering
Common filter parameters are defined in `common.ts`:
- Search queries (`q`)
- Source filtering (`src`, `platform`)
- Feature filtering (`has`)
- Sorting (`sort_by`, `order`)

### Timestamps
All timestamps are handled as ISO strings and can be converted to Date objects as needed.

## Integration

The schemas integrate seamlessly with:
- **API Services** - Automatic validation in service methods
- **React Query** - Type-safe hooks for data fetching
- **Forms** - Validation for user input
- **Components** - Type-safe props and state management