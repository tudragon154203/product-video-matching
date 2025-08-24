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
  // Disable SWC for macOS compatibility
  experimental: {
    swcPlugins: [],
  },
}

module.exports = nextConfig