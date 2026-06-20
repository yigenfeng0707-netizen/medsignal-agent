/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用 standalone 输出，供 Docker 生产镜像使用（独立可运行产物）
  output: "standalone",
};

export default nextConfig;
