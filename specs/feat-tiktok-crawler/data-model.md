# Data Model: TikTok Platform Integration

## Core Entities

### TikTokVideo Entity
Represents a single video retrieved from TikTok search results.

**Fields**:
- `id` (string): Unique video identifier from TikTok
- `caption` (string): Video caption/text content (may be empty)
- `authorHandle` (string): TikTok username/author handle
- `likeCount` (number): Number of likes on the video
- `uploadTime` (string): Video upload timestamp (ISO format)
- `webViewUrl` (string): Direct URL to view the video on TikTok

### TikTokSearchResponse Entity
Represents the response from TikTok Search API.

**Fields**:
- `results` (TikTokVideo[]): Array of TikTokVideo objects
- `totalResults` (number): Total number of results available
- `query` (string): Original search query executed
- `search_metadata` (object): Execution metadata containing:
  - `executed_path` (string): API endpoint path executed
  - `execution_time` (number): Execution time in milliseconds
  - `request_hash` (string): Unique hash of the request parameters

## Database Schema

### Videos Table (Existing)
The TikTok videos will be stored in the existing `videos` table with platform="tiktok":

```sql
videos (
    video_id UUID PRIMARY KEY,
    platform VARCHAR(20) NOT NULL, -- 'tiktok'
    url VARCHAR(500) NOT NULL,     -- webViewUrl
    title VARCHAR(500),            -- caption
    duration_s INTEGER,            -- NULL for TikTok (not available in search)
    job_id UUID NOT NULL
)
```

### Video Metadata Extension
TikTok-specific metadata can be stored as JSON in an extended metadata field:

```sql
video_metadata (
    video_id UUID PRIMARY KEY REFERENCES videos(video_id),
    platform_metadata JSONB NOT NULL, -- TikTok-specific fields
    created_at TIMESTAMP DEFAULT NOW()
)
```

**Platform Metadata Structure**:
```json
{
  "authorHandle": "@username",
  "likeCount": 12345,
  "uploadTime": "2024-01-01T12:00:00Z",
  "tiktokId": "video_123456789"
}
```

## API Contracts

### TikTok Search Request
```typescript
interface TikTokSearchRequest {
  query: string;
  numVideos?: number;      // Max 50, default: 10
  force_headful?: boolean; // Default: false
}
```

### TikTok Search Response
```typescript
interface TikTokSearchResponse {
  results: TikTokVideo[];
  totalResults: number;
  query: string;
  search_metadata: {
    executed_path: string;
    execution_time: number;
    request_hash: string;
  };
}
```

### TikTok Video Entity
```typescript
interface TikTokVideo {
  id: string;
  caption: string;
  authorHandle: string;
  likeCount: number;
  uploadTime: string; // ISO timestamp
  webViewUrl: string;
}
```

## Event Contracts

### Existing RabbitMQ Events
The TikTok crawler will use the existing event system:

**Event**: `videos.search.request` (VideosSearchRequest schema)
- Platform: "tiktok" included in platforms array
- Uses existing query structure with language-specific queries

**Event**: `videos.collections.completed`
- Emitted when video collection completes for all platforms
- Includes TikTok results along with other platforms

**Event**: `videos.keyframes.ready`
- Emitted for each video when keyframes are extracted
- Includes platform-specific metadata for TikTok videos

## Validation Rules

### Input Validation (Existing Schema)
- `job_id`: Required UUID string
- `industry`: Required string
- `queries`: Required object with `vi` and `zh` arrays
- `platforms`: Required array with "tiktok" as valid option
- `recency_days`: Required integer, minimum 1

### TikTok API Specific Validation
- `numVideos`: Optional, min 1, max 50, default 10 (passed to TikTok API)
- `force_headful`: Optional boolean, default false (passed to TikTok API)

### Response Validation
- `results`: Required array, max 50 items
- `totalResults`: Required number, >= 0
- Each `TikTokVideo` must have required fields
- `search_metadata` must contain execution details

### Business Rules
- Videos are processed in real-time as they stream
- Maximum 50 videos per search request
- 7-day data retention policy
- Retry logic: 3 attempts with exponential backoff