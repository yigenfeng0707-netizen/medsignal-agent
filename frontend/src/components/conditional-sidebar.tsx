"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { Sidebar, SidebarNav } from "@/components/sidebar";
import { UserSwitcher } from "@/components/user-switcher";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function ConditionalSidebar({ children }: { children: React.ReactNode }) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 lg:ml-64">
        {/* 顶部固定栏：小屏汉堡导航 + 用户切换器 */}
        <div className="sticky top-0 z-30 flex h-14 items-center justify-between gap-2 border-b border-slate-100 bg-white/80 px-3 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-2">
            {/* 小屏（<lg）：汉堡按钮唤起抽屉导航 */}
            <Sheet open={navOpen} onOpenChange={setNavOpen}>
              <SheetTrigger asChild>
                <button
                  aria-label="打开导航菜单"
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition-colors hover:bg-slate-100 lg:hidden"
                >
                  <Menu className="h-5 w-5" />
                </button>
              </SheetTrigger>
              <SheetContent side="left" className="w-72 bg-sidebar p-0">
                <SheetTitle className="sr-only">MedSignal 导航菜单</SheetTitle>
                <SidebarNav onNavigate={() => setNavOpen(false)} />
              </SheetContent>
            </Sheet>
            <span className="truncate text-sm font-medium text-slate-500">
              统一医疗智能体工作台
            </span>
          </div>
          <UserSwitcher />
        </div>
        {children}
      </main>
    </div>
  );
}
