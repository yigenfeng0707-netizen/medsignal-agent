/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用 standalone 输出，供 Docker 生产镜像使用（独立可运行产物）
  output: "standalone",
  // 魔搭创空间同域部署：ENABLE_API_PROXY=1 时把 /api/* 代理到容器内 FastAPI(8000)
  // 其他部署（Render/Vercel）使用 NEXT_PUBLIC_API_URL 绝对地址，不走此代理
  async rewrites() {
    if (process.env.ENABLE_API_PROXY === "1") {
      return [
        {
          source: "/api/:path*",
          destination: `${process.env.BACKEND_PROXY_TARGET || "http://127.0.0.1:8000"}/api/:path*`,
        },
      ];
    }
    return [];
  },
};

export default nextConfig;
