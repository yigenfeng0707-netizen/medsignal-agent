"use client";

import { useMemo } from "react";
import { Accessibility, Database, RefreshCw } from "lucide-react";

import { ApiStatusIndicator } from "@/components/api-status-indicator";
import { Card, CardContent } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";
import { useUser } from "@/lib/user-context";

export default function BodyArchivePage() {
  const { currentUser, userId } = useUser();
  const viewerUrl = useMemo(() => {
    const base = API_BASE || "";
    const params = new URLSearchParams({ patient: userId });
    return `${base}/digital-body/index.html?${params.toString()}`;
  }, [userId]);

  return (
    <div className="space-y-5 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Accessibility className="h-6 w-6 text-cyan-600" />
            <h1 className="text-2xl font-bold text-foreground">数字人体档案</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            将 {currentUser.name} 的既有就诊记录与追加资料按解剖部位整理展示
          </p>
        </div>
        <ApiStatusIndicator />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <Card className="border-cyan-100 bg-cyan-50/60">
          <CardContent className="flex items-center gap-3 p-4">
            <RefreshCw className="h-5 w-5 text-cyan-700" />
            <div>
              <div className="text-sm font-semibold">可交互 3D 解剖</div>
              <div className="text-xs text-muted-foreground">旋转、缩放、悬停和部位聚焦</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-slate-200">
          <CardContent className="flex items-center gap-3 p-4">
            <Database className="h-5 w-5 text-slate-700" />
            <div>
              <div className="text-sm font-semibold">统一健康档案</div>
              <div className="text-xs text-muted-foreground">复用 MedSignal 用户与就诊数据</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-amber-100 bg-amber-50/50 md:col-span-1">
          <CardContent className="p-4 text-xs leading-5 text-amber-900">
            仅整理展示已有资料，不自动检测或推断疾病，不构成临床诊断或治疗建议。
          </CardContent>
        </Card>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-[#020610] shadow-sm">
        <iframe
          key={userId}
          src={viewerUrl}
          title={`${currentUser.name}的数字人体档案`}
          className="h-[calc(100vh-19rem)] min-h-[640px] w-full border-0"
          allow="fullscreen"
        />
      </div>
    </div>
  );
}
