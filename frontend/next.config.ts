import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable streaming responses
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
    },
  },
  // Increase timeout for streaming
  httpAgentOptions: {
    keepAlive: true,
  },
}

export default nextConfig;