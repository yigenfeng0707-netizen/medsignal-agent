import { cn } from "@/lib/utils";

type DidaYiLogoProps = {
  className?: string;
  compact?: boolean;
  light?: boolean;
};

/** 嘀嗒医品牌标志：用户原创健康机器人。 */
export function DidaYiLogo({ className, compact = false, light = false }: DidaYiLogoProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className="relative h-12 w-14 shrink-0 overflow-hidden" aria-hidden="true">
        <img src="/branding/didayi-mascot.png" alt="" className="absolute inset-0 h-full w-full translate-y-[7%] scale-[1.27] object-contain" />
      </span>
      {!compact && (
        <div className="min-w-0">
          <div className={cn("text-xl font-bold leading-none tracking-[.04em]", light ? "text-slate-800" : "text-slate-900")}>嘀嗒医</div>
          <div className={cn("mt-1 text-[10px] tracking-[.08em]", light ? "text-slate-500" : "text-slate-500")}>让关键医疗信号，不再被错过</div>
        </div>
      )}
    </div>
  );
}
