const withNextIntl = require('next-intl/plugin')(
  // This is the default path to your i18n.ts file
  './i18n.ts'
);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: false, // Disabled due to macOS binary issues
  experimental: {
    swcPlugins: []
  },
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8888',
  },
}

module.exports = withNextIntl(nextConfig)