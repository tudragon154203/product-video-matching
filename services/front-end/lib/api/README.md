# API Client Architecture

This document outlines the modular API client architecture designed for scalability and maintainability.

## 📁 Directory Structure

```
lib/api/
├── index.ts                 # Main export file
├── client.ts               # Base axios client configuration
├── services/               # API service modules
│   ├── index.ts
│   ├── job.api.ts         # Job-related APIs (main-api)
│   ├── result.api.ts      # Results APIs (main-api)
│   └── feature.api.ts     # Features APIs (main-api)
├── utils/                  # API utilities and helpers
│   ├── index.ts
│   ├── phase.ts           # Phase-related utilities
│   ├── polling.ts         # Polling utilities
│   └── error-handling.ts  # Error handling utilities
└── README.md              # This file
```

## 🚀 Quick Start

### Basic Usage

```typescript
import { jobApi, resultsApiService, featureApiService } from '@/lib/api';

// Start a new job
const response = await jobApi.startJob({
  query: 'wireless headphones',
  top_amz: 10,
  top_ebay: 5,
  platforms: ['youtube'],
  recency_days: 30,
});

// Get job status
const status = await jobApi.getJobStatus(response.job_id);

// List all jobs
const jobs = await jobApi.listJobs({ limit: 20 });

// Get results (from main-api)
const results = await resultsApiService.getResults({
  min_score: 0.8,
  limit: 50,
});
```

### Phase Utilities

```typescript
import { getPhaseInfo, getPhasePercent, shouldPoll } from '@/lib/api';

const phase = 'matching';
const info = getPhaseInfo(phase);
console.log(info.label); // "Matching"
console.log(info.color); // "purple"

const percent = getPhasePercent(phase); // 80
const needsPolling = shouldPoll(phase); // true
```

### Error Handling

```typescript
import { handleApiError, getUserFriendlyMessage } from '@/lib/api';

try {
  const result = await jobApi.startJob(data);
} catch (error) {
  const apiError = handleApiError(error);
  const message = getUserFriendlyMessage(apiError);
  toast.error(message);
}
```

## 🏗️ Architecture Principles

### 1. **Modular Design**
- Each service has its own module (job, result, feature)
- Easy to add new services without modifying existing code
- Clear separation of concerns

### 2. **Type Safety**
- Full TypeScript support with Zod schema validation
- Compile-time error checking
- IntelliSense support

### 3. **Error Handling**
- Standardized error format across all APIs
- User-friendly error messages
- Retry logic for appropriate errors

### 4. **Configuration**
- Centralized API client configuration
- Environment-specific settings
- Request/response interceptors

## 📋 Service Modules

### JobApiService
Handles job-related operations with main-api:
- `startJob(request)` - Start a new matching job
- `getJobStatus(jobId)` - Get job status and progress
- `listJobs(params?)` - List jobs with pagination
- `healthCheck()` - Health check endpoint

### ResultsApiService
Handles results and data retrieval from main-api:
- `getResults(params?)` - Get matching results with filtering
- `getProduct(productId)` - Get product details
- `getVideo(videoId)` - Get video details
- `getMatch(matchId)` - Get match details
- `getEvidence(matchId)` - Get evidence image
- `getStats()` - Get system statistics

### FeatureApiService
Handles feature extraction monitoring from main-api:
- `getFeatureSummary(jobId)` - Get feature extraction progress
- `getProductImageFeatures(jobId, params?)` - Get product image features
- `getVideoFrameFeatures(jobId, params?)` - Get video frame features
- `getProductImageFeature(imgId)` - Get individual image features
- `getVideoFrameFeature(frameId)` - Get individual frame features

## 🛠️ Utilities

### Phase Utilities (`utils/phase.ts`)
- Phase information and UI properties
- Progress calculation
- Polling decision logic
- Phase state checking

### Polling Utilities (`utils/polling.ts`)
- Configurable polling strategies
- Exponential backoff support
- React Query integration
- Phase-specific polling configs

### Error Handling (`utils/error-handling.ts`)
- Axios error transformation
- Standardized error format
- User-friendly messages
- Retry logic

## 🔧 Configuration

### Environment Variables
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000      # main-api (includes results endpoints)
```

### Client Configuration
```typescript
import { createApiClient } from '@/lib/api';

// Custom client with different config
const customClient = createApiClient({
  baseURL: 'https://api.example.com',
  timeout: 60000,
});
```

## 📚 Migration Guide

### From Old `api.ts`
The old monolithic `api.ts` file has been replaced with a modular structure. Existing imports should continue to work:

```typescript
// Old (still works)
import { jobApi, getPhaseInfo } from '@/lib/api';

// New (recommended)
import { jobApiService, getPhaseInfo } from '@/lib/api';
```

### Updating Components
Components should gradually migrate to use the new service classes:

```typescript
// Old
import { jobApi } from '@/lib/api';

// New
import { jobApiService } from '@/lib/api';

// Usage remains the same
const jobs = await jobApiService.listJobs();
```

## 🔮 Future Enhancements

### React Query Hooks
Future versions may include pre-built React Query hooks:

```typescript
// Planned for future releases
import { useJobs, useJobStatus } from '@/lib/api/hooks';

const { data: jobs, isLoading } = useJobs();
const { data: status } = useJobStatus(jobId);
```

### Authentication
When authentication is added, the client will automatically handle:
- Token management
- Automatic token refresh
- Authentication redirects

### Caching
Enhanced caching strategies:
- Response caching
- Optimistic updates
- Cache invalidation

## 🧪 Testing

Each service module can be tested independently:

```typescript
import { jobApiService } from '@/lib/api';

// Mock the client for testing
jest.mock('@/lib/api/client');

test('should start job', async () => {
  // Test implementation
});
```

## 📖 Examples

### Complete Job Workflow
```typescript
import { 
  jobApiService, 
  getPhaseInfo, 
  shouldPoll 
} from '@/lib/api';

// Start job
const { job_id } = await jobApiService.startJob({
  query: 'bluetooth speakers',
  top_amz: 15,
  top_ebay: 10,
  platforms: ['youtube', 'tiktok'],
  recency_days: 60,
});

// Monitor progress
const pollStatus = async () => {
  const status = await jobApiService.getJobStatus(job_id);
  const phaseInfo = getPhaseInfo(status.phase);
  
  console.log(`Job ${job_id}: ${phaseInfo.label} (${status.percent}%)`);
  
  if (shouldPoll(status.phase)) {
    setTimeout(pollStatus, 5000);
  }
};

pollStatus();
```

### Error Handling with Retry
```typescript
import { 
  jobApiService, 
  handleApiError, 
  isRetryableError 
} from '@/lib/api';

const startJobWithRetry = async (data, maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await jobApiService.startJob(data);
    } catch (error) {
      const apiError = handleApiError(error);
      
      if (attempt === maxRetries || !isRetryableError(apiError)) {
        throw apiError;
      }
      
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
};
```