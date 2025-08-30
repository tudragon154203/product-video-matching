const withNextIntl = require('next-intl/plugin')(
  // This is the default path to your i18n.ts file
  './i18n.ts'
);

/** @type {import('next').NextConfig} */
const isDev = process.env.NODE_ENV !== 'production'
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
        hostname: 'localhost',
        port: '8888',
        pathname: '/files/**',
      },
      {
        protocol: 'http',
        hostname: '127.0.0.1',
        port: '8888',
        pathname: '/files/**',
      },
    ],
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8888'
  },
}

module.exports = withNextIntl(nextConfig)
