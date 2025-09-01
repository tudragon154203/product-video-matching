# Frontend Microservice - Product Video Matching

This is the UI microservice for the product video matching system.

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: TailwindCSS + shadcn/ui
- **State Management**: TanStack Query
- **Validation**: Zod
- **Testing**: Jest + React Testing Library + Playwright
- **Animations**: @formkit/auto-animate

## Animation Features

The application includes smooth animations powered by `@formkit/auto-animate` to enhance user experience during list updates and state changes.

### Configuration

Animations are enabled by default and respect the user's reduced motion preference (`prefers-reduced-motion`).

### Components with Animations

- **VideosPanel**: Smooth transitions when video lists update or filter
- **ProductsPanel**: Animated product list changes during pagination or filtering
- **JobSidebar**: Smooth job list updates and status changes
- **CommonPanel**: Consistent animation behavior across all panel layouts
- **ThumbnailImage**: Subtle animations for image loading states

### Implementation Details

- Uses `useAutoAnimateList` hook for list container animations
- Uses `useAutoAnimateItem` hook for individual item animations
- Respects user motion preferences via `disrespectUserMotionPreference` option
- SSR-compatible with proper client-side checks

### Custom Hooks

- `useAutoAnimateList`: For animating list containers
- `useAutoAnimateItem`: For animating individual list items

Both hooks provide consistent animation behavior and respect user motion preferences across the application.

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

### Switching Between Development and Production

The Dockerfile supports multi-stage builds with separate `development` and `production` targets.

**Development Mode (with hot reloading):**
```bash
# Uses target: development from Dockerfile
docker compose -f infra/pvm/docker-compose.dev.yml up front-end
```

**Production Mode (optimized build):**
```bash
# Override target to production
docker compose -f infra/pvm/docker-compose.dev.yml up front-end \
  --build-arg target=production

# Or build with production target
docker compose -f infra/pvm/docker-compose.dev.yml build \
  --target production front-end
```

**Key Differences:**
- **Development**: Hot reloading, source code mounted as volumes, faster startup
- **Production**: Optimized build, standalone output, smaller image size, no volumes

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
