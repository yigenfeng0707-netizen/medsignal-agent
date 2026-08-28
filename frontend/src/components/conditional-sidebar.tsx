"use client";

import { Sidebar } from "@/components/sidebar";
import { UserSwitcher } from "@/components/user-switcher";
import { Activity, Bell } from "lucide-react";

export function ConditionalSidebar({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-64 flex-1 bg-sky-50/70">
        {/* 顶部固定栏：用户切换器 */}
        <div className="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-sky-100/90 bg-white/80 px-7 backdrop-blur-xl">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-500">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-cyan-50 text-cyan-600"><Activity className="h-4 w-4" /></span>
            嘀嗒医 · 智能健康工作台
          </div>
          <div className="flex items-center gap-3">
            <button aria-label="消息提醒" className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-sky-100 bg-white text-slate-500 shadow-sm transition hover:bg-sky-50 hover:text-cyan-600">
              <Bell className="h-4 w-4" />
              <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-[#FF7A59]" />
            </button>
            <UserSwitcher />
          </div>
        </div>
        {children}
      </main>
    </div>
  );
}
