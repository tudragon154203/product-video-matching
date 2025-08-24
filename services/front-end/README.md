# Frontend Microservice - Product Video Matching

This is the UI microservice for the product video matching system.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS + shadcn/ui
- **State Management**: TanStack Query
- **Validation**: Zod
- **Testing**: Jest + React Testing Library + Playwright

## Development

### Prerequisites

- Node.js 18+ 
- Docker
- Docker Compose

### Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Stop the development server
# Press Ctrl+C in the terminal where npm run dev is running

# Build for production
npm run build

# Start production server
npm start

# Stop the production server
# Press Ctrl+C in the terminal where npm start is running
# OR send SIGTERM: kill <process_id>
# OR send SIGKILL: kill -9 <process_id> (force stop)
```

## API Integration

Base URL: `NEXT_PUBLIC_API_BASE_URL` (environment variable)

### Endpoints

- `POST /start-job` - Start a new matching job
- `GET /status/{job_id}` - Get job status

### Polling Strategy

- Poll `/status/{job_id}` every 5 seconds
- Stop polling when phase is `completed` or `failed`
- Display timestamps in GMT+7

## Docker

See `Dockerfile` for container configuration.

## Testing

```bash
# Run tests
npm test

# Run integration tests
npm run test:e2e

# Type checking
npm run type-check

# Linting
npm run lint
```