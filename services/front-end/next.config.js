const withNextIntl = require('next-intl/plugin')(
  // This is the default path to your i18n.ts file
  './i18n.ts'
);

/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production'
// Derive API host/port from NEXT_PUBLIC_API_BASE_URL so Next/Image allows it
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8888'
let apiHost = 'localhost'
let apiPort = '8888'
try {
  const u = new URL(apiBase)
  apiHost = u.hostname || 'localhost'
  // URL.port may be empty if default for protocol; normalize
  apiPort = u.port || (u.protocol === 'https:' ? '443' : '80')
} catch (_) {
  // Fallbacks above remain
}
const nextConfig = {
  reactStrictMode: true,
  swcMinify: false, // Disabled due to macOS binary issues
  experimental: {
    swcPlugins: []
  },
  images: {
    // In dev, bypass Next/Image optimization to avoid server-side
    // fetching localhost:8888 from inside the container
    unoptimized: isDev,
    remotePatterns: [
      {
        protocol: 'http',
        hostname: apiHost,
        port: apiPort,
        pathname: '/files/**',
      },
      // Also allow 127.0.0.1 with same port for local dev convenience
      {
        protocol: 'http',
        hostname: '127.0.0.1',
        port: apiPort,
        pathname: '/files/**',
      },
    ],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: apiBase,
    NEXT_PUBLIC_ENABLE_ROUTE_LOADING: '1', // Enable loading screen by default for testing
  },
}

module.exports = withNextIntl(nextConfig)
