"use client";

import { Sidebar } from "@/components/sidebar";
import { UserSwitcher } from "@/components/user-switcher";

export function ConditionalSidebar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1">
        {/* 顶部固定栏：用户切换器 */}
        <div className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-100 bg-white/80 px-6 backdrop-blur">
          <span className="text-sm font-medium text-slate-500">统一医疗智能体工作台</span>
          <UserSwitcher />
        </div>
        {children}
      </main>
    </div>
  );
}
