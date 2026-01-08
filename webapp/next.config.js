/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    unoptimized: true,
    domains: ["media.licdn.com", "media-exp1.licdn.com"],
  },
};

module.exports = nextConfig;
