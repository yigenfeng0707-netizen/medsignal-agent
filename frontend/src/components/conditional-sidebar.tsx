"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { UserSwitcher } from "@/components/user-switcher";

export function ConditionalSidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isHomePage = pathname === "/";

  if (isHomePage) {
    // 首页：右上角放用户切换器
    return (
      <div className="relative min-h-screen">
        <div className="absolute right-4 top-4 z-40">
          <UserSwitcher />
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1">
        {/* 顶部固定栏：用户切换器 */}
        <div className="sticky top-0 z-30 flex h-14 items-center justify-end border-b border-slate-100 bg-white/80 px-6 backdrop-blur">
          <UserSwitcher />
        </div>
        {children}
      </main>
    </div>
  );
}
