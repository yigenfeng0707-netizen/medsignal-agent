"use client";

/**
 * 用户切换器：路演 Demo 神器
 * 顶部下拉，一键切换 10 个用户画像，全站数据联动。
 * 使用原生 details/summary 实现下拉，避免引入新依赖。
 */

import { Fragment, useState, useEffect, useRef } from "react";
import { Users, ChevronDown, Check } from "lucide-react";
import { useUser } from "@/lib/user-context";
import { cn } from "@/lib/utils";

export function UserSwitcher() {
  const { currentUser, users, setUserId } = useUser();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // 点击外部关闭
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium shadow-sm transition hover:bg-slate-50"
        aria-label="切换演示用户"
      >
        <Users className="h-4 w-4 text-blue-600" />
        <span className="hidden sm:inline">
          <span className="text-slate-500">演示用户：</span>
          <span className="font-semibold text-slate-900">{currentUser.name}</span>
        </span>
        <span className="sm:hidden font-semibold">{currentUser.name}</span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-slate-400 transition-transform",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 max-h-[70vh] overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-xl">
          <div className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-slate-700 border-b border-slate-100 mb-1">
            <Users className="h-4 w-4 text-blue-600" />
            切换演示用户
          </div>
          {users.map((u) => (
            <button
              key={u.id}
              onClick={() => {
                setUserId(u.id);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition hover:bg-slate-50",
                u.id === currentUser.id && "bg-blue-50"
              )}
            >
              <div
                className={cn(
                  "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold",
                  u.gender === "女"
                    ? "bg-pink-100 text-pink-700"
                    : "bg-blue-100 text-blue-700"
                )}
              >
                {u.name.slice(-1)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-slate-900">{u.name}</span>
                  <span className="text-xs text-slate-400">
                    {u.age}岁 · {u.city}
                  </span>
                </div>
                <div className="text-xs text-slate-500 truncate">
                  {u.insurance_type} · {u.employee_status}
                  {u.conditions.length > 0 && (
                    <span className="ml-1 text-orange-600">
                      · {u.conditions.join("、")}
                    </span>
                  )}
                </div>
              </div>
              {u.id === currentUser.id && (
                <Check className="h-4 w-4 shrink-0 text-blue-600" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
