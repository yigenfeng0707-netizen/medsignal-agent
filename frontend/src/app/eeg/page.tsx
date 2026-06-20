"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Brain,
  Activity,
  Zap,
  Moon,
  Eye,
  HeartPulse,
  Play,
  Square,
  Loader2,
  Sparkles,
  ShieldCheck,
  TrendingUp,
  ChevronRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReactEChartsCore from "echarts-for-react/lib/core";
import * as echarts from "echarts/core";
import { BarChart, LineChart, RadarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  createEEGSession,
  getLatestEEG,
  getEEGHistory,
  getEEGRealtime,
  getEEGMentalStates,
} from "@/lib/api";
import { useUser } from "@/lib/user-context";
import { ApiStatusIndicator } from "@/components/api-status-indicator";
import type {
  EEGSession,
  EEGMentalState,
  EEGRealtimeChunk,
  EEGTrendPoint,
} from "@/lib/mock-data";

echarts.use([
  BarChart,
  LineChart,
  RadarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  CanvasRenderer,
]);

const fadeIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

// 通道颜色（Muse 4 通道布局）
const CHANNEL_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"];
const CHANNEL_LABELS: Record<string, string> = {
  TP9: "左耳后",
  AF7: "左前额",
  AF8: "右前额",
  TP10: "右耳后",
};

// 频段中文标签 + 颜色
const BAND_META: Record<string, { label: string; color: string; desc: string }> = {
  delta: { label: "δ 波", color: "#6366f1", desc: "深度睡眠" },
  theta: { label: "θ 波", color: "#0ea5e9", desc: "疲劳/记忆" },
  alpha: { label: "α 波", color: "#10b981", desc: "放松/清醒" },
  beta: { label: "β 波", color: "#f59e0b", desc: "专注/焦虑" },
  gamma: { label: "γ 波", color: "#ef4444", desc: "高度认知" },
};

function getScoreColor(score: number, reverse = false): string {
  // reverse=true：分数越低越危险（如睡眠质量）
  const s = reverse ? 100 - score : score;
  if (s >= 70) return "#22c55e";
  if (s >= 40) return "#f59e0b";
  return "#ef4444";
}

function getScoreLabel(score: number, reverse = false): string {
  const s = reverse ? 100 - score : score;
  if (s >= 70) return "良好";
  if (s >= 40) return "一般";
  return "需关注";
}

function MetricRing({
  score,
  label,
  icon: Icon,
  reverse = false,
  unit = "/100",
}: {
  score: number;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  reverse?: boolean;
  unit?: string;
}) {
  const size = 120;
  const strokeWidth = 8;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score, reverse);

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="#f3f4f6" strokeWidth={strokeWidth} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-1000"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <Icon className="h-5 w-5 mb-1" style={{ color }} />
          <span className="text-2xl font-bold" style={{ color }}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      <div className="mt-2 text-center">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs" style={{ color }}>
          {getScoreLabel(score, reverse)}
          {unit}
        </p>
      </div>
    </div>
  );
}

export default function EEGPage() {
  const [session, setSession] = useState<EEGSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [realtimeChunks, setRealtimeChunks] = useState<EEGRealtimeChunk[]>([]);
  const [trend, setTrend] = useState<EEGTrendPoint[]>([]);
  const [mentalStates, setMentalStates] = useState<EEGMentalState[]>([]);
  const [selectedState, setSelectedState] = useState<string>("auto");
  const [isStreaming, setIsStreaming] = useState(false);
  const streamTimerRef = useRef<NodeJS.Timeout | null>(null);
  const streamSeedRef = useRef(0);
  const { userId, currentUser } = useUser();

  // 加载初始数据
  useEffect(() => {
    setLoading(true);
    Promise.all([getLatestEEG(userId), getEEGHistory(userId), getEEGMentalStates()]).then(
      ([latest, history, states]) => {
        if (latest) setSession(latest);
        if (history?.trend) setTrend(history.trend);
        if (states?.length) setMentalStates(states);
        setLoading(false);
      },
    );
  }, [userId]);

  // 实时流采集
  const startStream = useCallback(() => {
    if (isStreaming) return;
    setIsStreaming(true);
    streamSeedRef.current = 0;
    setRealtimeChunks([]);

    const tick = async () => {
      const state = selectedState === "auto" ? "relaxed" : selectedState;
      const chunk = await getEEGRealtime(userId, state, streamSeedRef.current);
      if (chunk) {
        setRealtimeChunks((prev) => [...prev.slice(-30), chunk]); // 保留最近 30 个块
      }
      streamSeedRef.current += 1;
    };

    tick();
    streamTimerRef.current = setInterval(tick, 1000);
  }, [isStreaming, selectedState, userId]);

  const stopStream = useCallback(() => {
    setIsStreaming(false);
    if (streamTimerRef.current) {
      clearInterval(streamTimerRef.current);
      streamTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => stopStream();
  }, [stopStream]);

  // 发起完整采集会话
  const handleCollect = async () => {
    setCollecting(true);
    stopStream();
    const result = await createEEGSession(userId, selectedState, 4);
    if (result) {
      setSession(result);
      // 刷新历史趋势
      const history = await getEEGHistory(userId);
      if (history?.trend) setTrend(history.trend);
    }
    setCollecting(false);
  };

  // 波形图配置（4 通道）
  const waveformOption = {
    tooltip: { trigger: "axis" as const },
    legend: {
      data: (session?.channels || ["TP9", "AF7", "AF8", "TP10"]).map((c) => CHANNEL_LABELS[c] || c),
      top: 0,
      textStyle: { fontSize: 11 },
    },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: "value" as const,
      name: "采样点",
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: "value" as const,
      name: "μV",
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: "#f3f4f6" } },
    },
    series: (session?.waveform || []).map((ch, i) => ({
      name: CHANNEL_LABELS[ch.channel] || ch.channel,
      type: "line",
      showSymbol: false,
      smooth: true,
      lineStyle: { width: 1.2, color: CHANNEL_COLORS[i % 4] },
      itemStyle: { color: CHANNEL_COLORS[i % 4] },
      data: ch.data.map((p) => [p.i, Number(p.v.toFixed(2))]),
    })),
  };

  // 频段功率柱状图
  const bandPowerOption = {
    tooltip: { trigger: "axis" as const },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { top: 40, right: 20, bottom: 30, left: 50 },
    xAxis: {
      type: "category" as const,
      data: Object.keys(session?.avg_band_powers || {}).map((b) => BAND_META[b]?.label || b),
      axisLabel: { fontSize: 11 },
    },
    yAxis: { type: "value" as const, name: "功率", axisLabel: { fontSize: 10 } },
    series: [
      {
        name: "平均功率",
        type: "bar",
        data: Object.entries(session?.avg_band_powers || {}).map(([b, v]) => ({
          value: Number(v.toFixed(3)),
          itemStyle: { color: BAND_META[b]?.color || "#888" },
        })),
        barWidth: "50%",
        label: { show: true, position: "top" as const, fontSize: 10 },
      },
    ],
  };

  // 趋势图（4 维时序）
  const trendOption = {
    tooltip: { trigger: "axis" as const },
    legend: { top: 0, textStyle: { fontSize: 11 } },
    grid: { top: 40, right: 20, bottom: 30, left: 40 },
    xAxis: {
      type: "category" as const,
      data: trend.map((_, i) => `第${i + 1}次`),
      axisLabel: { fontSize: 10 },
    },
    yAxis: { type: "value" as const, min: 0, max: 100, axisLabel: { fontSize: 10 } },
    series: [
      {
        name: "压力指数",
        type: "line",
        data: trend.map((t) => t.stress_index),
        smooth: true,
        lineStyle: { color: "#ef4444", width: 2 },
        itemStyle: { color: "#ef4444" },
      },
      {
        name: "注意力",
        type: "line",
        data: trend.map((t) => t.attention_index),
        smooth: true,
        lineStyle: { color: "#3b82f6", width: 2 },
        itemStyle: { color: "#3b82f6" },
      },
      {
        name: "睡眠质量",
        type: "line",
        data: trend.map((t) => t.sleep_quality),
        smooth: true,
        lineStyle: { color: "#6366f1", width: 2 },
        itemStyle: { color: "#6366f1" },
      },
      {
        name: "认知负荷",
        type: "line",
        data: trend.map((t) => t.cognitive_load),
        smooth: true,
        lineStyle: { color: "#f59e0b", width: 2 },
        itemStyle: { color: "#f59e0b" },
      },
    ],
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <motion.div {...fadeIn}>
          <h1 className="text-2xl font-bold text-foreground">脑电健康</h1>
          <p className="text-sm text-muted-foreground">BCI×医保创新 · 脑电采集 → 健康评估 → 医保联动</p>
        </motion.div>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  const metrics = session?.metrics;
  const alerts = session?.alerts || [];
  const policyLinks = session?.policy_links || [];

  return (
    <div className="p-6 space-y-6">
      {/* 页头 */}
      <motion.div {...fadeIn}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <Brain className="h-6 w-6 text-purple-500" />
              脑电健康
            </h1>
            <p className="text-sm text-muted-foreground">
              BCI×医保创新 · 脑电采集 → 健康评估 → 医保联动 · {currentUser?.name || "用户"}
            </p>
          </div>
          <ApiStatusIndicator />
        </div>
      </motion.div>

      {/* 采集控制栏 */}
      <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.05 }}>
        <Card className="bg-gradient-to-r from-purple-50 to-blue-50 border-purple-100">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-purple-500" />
                <span className="text-sm font-medium">采集场景：</span>
                <select
                  value={selectedState}
                  onChange={(e) => setSelectedState(e.target.value)}
                  className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-purple-400"
                >
                  <option value="auto">智能推荐（根据画像）</option>
                  {mentalStates.map((s) => (
                    <option key={s.key} value={s.key}>
                      {s.label}（压力{s.stress}/注意力{s.attention}）
                    </option>
                  ))}
                </select>
              </div>
              <Button
                onClick={handleCollect}
                disabled={collecting}
                className="bg-purple-600 hover:bg-purple-700 text-white"
              >
                {collecting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    采集中...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    发起 4 秒采集
                  </>
                )}
              </Button>
              <Button
                onClick={isStreaming ? stopStream : startStream}
                variant={isStreaming ? "destructive" : "outline"}
              >
                {isStreaming ? (
                  <>
                    <Square className="h-4 w-4 mr-2" />
                    停止实时流
                  </>
                ) : (
                  <>
                    <Activity className="h-4 w-4 mr-2" />
                    实时流模拟
                  </>
                )}
              </Button>
              {session && (
                <Badge variant="secondary" className="ml-auto">
                  最近采集：{session.mental_state_label} · {session.duration_seconds}s ·{" "}
                  {session.sample_rate}Hz · {session.channels.length} 通道
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* 实时流波形（采集时显示） */}
      <AnimatePresence>
        {isStreaming && realtimeChunks.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
          >
            <Card className="bg-white border-purple-100">
              <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <Activity className="h-4 w-4 text-purple-500 animate-pulse" />
                  实时脑电波形（{realtimeChunks.length} 个数据块）
                </CardTitle>
              </CardHeader>
              <CardContent>
                <RealtimeWaveform chunks={realtimeChunks} />
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 四维健康指标 */}
      {metrics && (
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.1 }}>
          <Card className="bg-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Brain className="h-4 w-4 text-purple-500" />
                脑电健康四维指标
                <Badge variant="outline" className="ml-2">
                  情绪：{metrics.emotion?.label || "平稳"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-4">
                <MetricRing score={metrics.stress_index} label="压力指数" icon={Zap} />
                <MetricRing score={metrics.attention_index} label="注意力" icon={Eye} />
                <MetricRing score={metrics.sleep_quality} label="睡眠质量" icon={Moon} reverse />
                <MetricRing score={metrics.cognitive_load} label="认知负荷" icon={Brain} />
              </div>
              {metrics.ratios && (
                <div className="mt-4 grid grid-cols-4 gap-2 text-xs text-muted-foreground">
                  <div className="text-center p-2 rounded bg-gray-50">
                    α/β = {metrics.ratios.alpha_beta}
                  </div>
                  <div className="text-center p-2 rounded bg-gray-50">
                    θ/β = {metrics.ratios.theta_beta}
                  </div>
                  <div className="text-center p-2 rounded bg-gray-50">
                    慢波占比 = {(metrics.ratios.slow_wave_ratio * 100).toFixed(1)}%
                  </div>
                  <div className="text-center p-2 rounded bg-gray-50">
                    快波占比 = {(metrics.ratios.fast_wave_ratio * 100).toFixed(1)}%
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* 波形 + 频段功率 */}
      <div className="grid grid-cols-2 gap-6">
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.15 }}>
          <Card className="bg-white h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Activity className="h-4 w-4 text-blue-500" />
                4 通道脑电波形
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ReactEChartsCore
                echarts={echarts}
                option={waveformOption}
                style={{ height: 280 }}
                notMerge
              />
            </CardContent>
          </Card>
        </motion.div>

        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.2 }}>
          <Card className="bg-white h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                五频段功率谱
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ReactEChartsCore
                echarts={echarts}
                option={bandPowerOption}
                style={{ height: 280 }}
                notMerge
              />
              <div className="mt-2 grid grid-cols-5 gap-1 text-xs">
                {Object.entries(BAND_META).map(([k, v]) => (
                  <div key={k} className="text-center p-1.5 rounded bg-gray-50">
                    <div className="font-medium" style={{ color: v.color }}>
                      {v.label}
                    </div>
                    <div className="text-muted-foreground text-[10px]">{v.desc}</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* 脑电预警 */}
      {alerts.length > 0 && (
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.25 }}>
          <Card className="bg-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <HeartPulse className="h-4 w-4 text-red-500" />
                脑电健康预警
                <Badge variant="secondary">{alerts.length} 项</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                {alerts.map((alert, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.3 + i * 0.05 }}
                    className={`p-3 rounded-lg border-l-4 ${
                      alert.level === "high"
                        ? "border-l-red-500 bg-red-50/50"
                        : alert.level === "medium"
                          ? "border-l-yellow-500 bg-yellow-50/50"
                          : "border-l-green-500 bg-green-50/50"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-lg">{alert.icon}</span>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-semibold text-foreground">{alert.title}</h4>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {alert.description || alert.desc}
                        </p>
                        {alert.suggestion && (
                          <p className="text-xs text-purple-600 mt-1.5">💡 {alert.suggestion}</p>
                        )}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* 医保政策联动（核心创新） */}
      {policyLinks.length > 0 && (
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.3 }}>
          <Card className="bg-gradient-to-br from-purple-50 to-blue-50 border-purple-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-purple-600" />
                脑电异常 → 医保政策联动
                <Badge className="bg-purple-600 text-white">BCI×医保核心创新</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {policyLinks.map((link, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.35 + i * 0.05 }}
                    className="p-4 rounded-lg bg-white border border-purple-100 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-foreground">{link.title}</h4>
                          <Badge variant="outline" className="text-xs text-purple-600 border-purple-300">
                            {link.policy_hint}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">
                          {link.description}
                        </p>
                        <p className="text-xs text-purple-700 mt-1.5">💡 {link.suggestion}</p>
                        {link.related_policies.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {link.related_policies.map((p, j) => (
                              <span
                                key={j}
                                className="text-[10px] px-2 py-0.5 rounded-full bg-purple-100 text-purple-700"
                              >
                                {p}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <ChevronRight className="h-4 w-4 text-purple-400 flex-shrink-0 mt-1" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* 历史趋势 */}
      {trend.length > 0 && (
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.35 }}>
          <Card className="bg-white">
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-500" />
                脑电健康趋势
                <Badge variant="secondary">最近 {trend.length} 次采集</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ReactEChartsCore
                echarts={echarts}
                option={trendOption}
                style={{ height: 280 }}
                notMerge
              />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* 摘要 */}
      {session?.summary && (
        <motion.div {...fadeIn} transition={{ duration: 0.4, delay: 0.4 }}>
          <Card className="bg-gray-50/50">
            <CardContent className="p-4">
              <div className="flex items-start gap-2">
                <Brain className="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-muted-foreground leading-relaxed">{session.summary}</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}

// 实时波形组件（滚动显示最近数据块）
function RealtimeWaveform({ chunks }: { chunks: EEGRealtimeChunk[] }) {
  const option = {
    animation: false,
    tooltip: { trigger: "axis" as const },
    grid: { top: 10, right: 10, bottom: 20, left: 40 },
    xAxis: {
      type: "value" as const,
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: "value" as const,
      name: "μV",
      nameTextStyle: { fontSize: 10 },
      axisLabel: { fontSize: 10 },
      splitLine: { lineStyle: { color: "#f3f4f6" } },
    },
    series: [
      {
        type: "line",
        showSymbol: false,
        smooth: true,
        lineStyle: { width: 1.2, color: "#8b5cf6" },
        itemStyle: { color: "#8b5cf6" },
        areaStyle: { color: "rgba(139, 92, 246, 0.1)" },
        data: chunks.flatMap((c, ci) =>
          c.waveform.map((p) => [ci * 64 + p.i, Number(p.v.toFixed(2))]),
        ),
      },
    ],
  };
  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      style={{ height: 200 }}
      notMerge
    />
  );
}
