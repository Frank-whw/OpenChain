/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
  // 移除 experimental 配置，因为 app 目录在新版本已经是默认的
  // experimental: {
  //   appDir: true,
  // },
}

export default nextConfig
