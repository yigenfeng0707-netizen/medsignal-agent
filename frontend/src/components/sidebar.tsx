"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Home,
  Shield,
  Heart,
  FileText,
  BookOpen,
  Lock,
  Network,
  Brain,
  ScanLine,
} from "lucide-react";

const navItems = [
  { href: "/", label: "首页", icon: Home },
  { href: "/coverage", label: "权益全景", icon: Shield },
  { href: "/health", label: "健康画像", icon: Heart },
  { href: "/eeg", label: "脑电健康", icon: Brain },
  { href: "/imaging", label: "影像标注", icon: ScanLine },
  { href: "/claims", label: "报销预审", icon: FileText },
  { href: "/policy", label: "政策匹配", icon: BookOpen },
  { href: "/security", label: "数据授权", icon: Lock },
  { href: "/security/data-space", label: "可信数据空间", icon: Network },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-sidebar-border bg-sidebar">
      <div className="flex h-16 items-center gap-2 border-b border-sidebar-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Shield className="h-5 w-5 text-primary-foreground" />
        </div>
        <span className="text-lg font-bold text-sidebar-foreground">
          MedSignal
        </span>
      </div>
      <nav className="flex flex-col gap-1 p-3">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <item.icon className={cn("h-5 w-5", isActive && "text-primary")} />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="absolute bottom-0 left-0 right-0 border-t border-sidebar-border p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Heart className="h-4 w-4" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-sidebar-foreground">
              MedSignal 助手
            </span>
            <span className="text-xs text-sidebar-foreground/50">
              关键医疗信号识别 × 患者信息连接
            </span>
          </div>
        </div>
      </div>
    </aside>
  );
}
