// 医保智脑 - API 客户端层
// 优先调用后端 API，后端不可用时自动降级为模拟数据

import {
  mockCoverageSummary,
  mockHealthProfile,
  mockOCRResult,
  mockPreReviewResult,
  mockClaimsPreReview,
  mockPolicyMatch,
  mockSecurityOverview,
  mockChatResponses,
  type CoverageSummary,
  type HealthProfile,
  type HealthAlert,
  type TrendPoint,
  type OCRResult,
  type PreReviewResult,
  type PolicyMatch,
  type SecurityOverview,
  type EEGSession,
  type EEGHistory,
  type EEGRealtimeChunk,
  type EEGMentalState,
  type EEGPolicyLink,
  mockImagingStudy,
  mockImagingStudyTypes,
  mockImagingRecords,
  mockImagingPolicyLinks,
  type ImagingFindingItem,
  type ImagingReportData,
  type ImagingPolicyLink,
  type ImagingStudyResponse,
  type ImagingStudyTypeInfo,
  type ImagingRecordItem,
} from "./mock-data";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ==================== API 状态检测 ====================

let _apiReachable: boolean | null = null;

/** 检测后端 API 是否可达（超时 60s，兼容 Render 免费套餐冷启动） */
export async function getApiStatus(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      method: "GET",
      signal: AbortSignal.timeout(60000),
    });
    _apiReachable = res.ok;
  } catch {
    _apiReachable = false;
  }
  return _apiReachable;
}

/** 获取缓存的 API 状态（同步） */
export function getCachedApiStatus(): boolean | null {
  return _apiReachable;
}

// ==================== 通用请求封装 ====================

async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      signal: options?.signal ?? AbortSignal.timeout(90000),
    });
    if (!res.ok) return null;
    // 防止 Render 冷启动返回 HTML 插页导致 JSON 解析失败
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

async function apiUpload<T>(
  path: string,
  file: File,
): Promise<T | null> {
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(120000),
    });
    if (!res.ok) return null;
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// ==================== 类型 ====================

export interface ChatRequest {
  message: string;
  user_id: string;
  conversation_id?: string;
}

export interface ChatResponse {
  agent_type: string;
  response: string;
  data: Record<string, unknown>;
  suggestions: string[];
  conversation_id?: string;
  evidence?: Array<Record<string, unknown>>;
  user_profile?: { name: string; age: number; insurance_type: string; chronic_diseases: string[] } | null;
}

// ==================== API 函数 ====================

/** 发送聊天消息 */
export async function sendChatMessage(
  req: ChatRequest,
): Promise<ChatResponse> {
  const data = await apiFetch<ChatResponse>("/api/agents/chat", {
    method: "POST",
    body: JSON.stringify(req),
  });

  if (data) return data;

  // 降级：使用模拟数据
  const mock = mockChatResponses[req.message];
  return {
    agent_type: mock?.agent || "医保智脑",
    response:
      mock?.content ||
      "收到您的问题，正在为您分析中...我会尽快给出详细解答。",
    data: {},
    suggestions: [],
  };
}

/** 获取权益全景 */
export async function getCoverageSummary(
  userId: string,
): Promise<CoverageSummary> {
  const data = await apiFetch<CoverageSummary & { payment_history_values?: number[] }>(
    `/api/coverage/${userId}`,
  );
  if (data) {
    // 后端真实返回的是对象数组，前端柱状图需要 number[]，做兼容转换
    const ph = data.payment_history as unknown;
    if (Array.isArray(ph) && ph.length > 0 && typeof ph[0] === "object") {
      data.payment_history = (ph as { personal_amount?: number }[]).map(
        (p) => p.personal_amount ?? 0,
      );
    } else if (data.payment_history_values && Array.isArray(data.payment_history_values)) {
      data.payment_history = data.payment_history_values as unknown as number[];
    }
    return data;
  }
  return mockCoverageSummary;
}

/** 获取健康画像 */
export async function getHealthProfile(
  userId: string,
): Promise<HealthProfile> {
  const data = await apiFetch<HealthProfile>(
    `/api/health/${userId}/profile`,
  );
  if (data) return data;
  return mockHealthProfile;
}

/** 获取健康预警 */
export async function getHealthAlerts(
  userId: string,
): Promise<HealthAlert[]> {
  const data = await apiFetch<{ alerts: HealthAlert[] }>(
    `/api/health/${userId}/alerts`,
  );
  if (data?.alerts) return data.alerts;
  return mockHealthProfile.alerts;
}

/** 获取健康趋势 */
export async function getHealthTrends(
  userId: string,
): Promise<TrendPoint[]> {
  const data = await apiFetch<{
    trends?: { monthly_costs: { month: string; amount: number }[] };
    health_trend?: TrendPoint[];
  }>(`/api/health/${userId}/trends`);
  // 优先用后端的 health_trend（真实健康评分趋势）
  if (data?.health_trend && data.health_trend.length > 0) {
    return data.health_trend.map((p) => ({
      month: (p.month || "").slice(5) + "月",
      score: p.score,
    }));
  }
  if (data?.trends?.monthly_costs) {
    return data.trends.monthly_costs.map((p, i) => ({
      month: p.month.slice(5) + "月",
      score: Math.max(50, Math.min(100, 80 - i * 2)),
    }));
  }
  return mockHealthProfile.trend_data;
}

/** 上传发票 OCR 识别 */
export async function uploadReceipt(file: File): Promise<OCRResult> {
  const data = await apiUpload<{ ocr_result: Record<string, unknown>; confidence: number }>(
    "/api/claims/ocr",
    file,
  );
  if (data?.ocr_result) {
    const r = data.ocr_result;
    return {
      hospital: (r.hospital as string) || "",
      date: (r.visit_date as string) || "",
      patient: (r.patient_name as string) || "",
      department: (r.diagnosis as string) || "",
      items: ((r.items as { name: string; amount: number }[]) || []).map((it) => ({
        name: it.name,
        price: it.amount,
      })),
      total: (r.total_amount as number) || 0,
      confidence: data.confidence,
    };
  }
  return mockOCRResult;
}

/** 报销预审 */
export async function preReviewClaim(
  claimData: Record<string, unknown>,
): Promise<PreReviewResult> {
  const data = await apiFetch<PreReviewResult>("/api/claims/pre-review", {
    method: "POST",
    body: JSON.stringify(claimData),
  });
  if (data) return data;
  return mockPreReviewResult;
}

/** 获取政策匹配 */
export async function getPolicyMatches(
  userId: string,
): Promise<PolicyMatch> {
  const data = await apiFetch<PolicyMatch>(
    `/api/policy/match/${userId}`,
  );
  if (data) return data;
  return mockPolicyMatch;
}

/** 搜索政策 */
export async function searchPolicies(query: string): Promise<PolicyMatch> {
  const data = await apiFetch<PolicyMatch>("/api/policy/search", {
    method: "POST",
    body: JSON.stringify({ keyword: query }),
  });
  if (data) return data;
  // 降级：在模拟数据中过滤
  const filtered = mockPolicyMatch.policies.filter(
    (p) =>
      p.title.includes(query) ||
      p.category.includes(query) ||
      p.matchReason.includes(query),
  );
  return { ...mockPolicyMatch, policies: filtered };
}

/** 获取数据授权总览 */
export async function getSecurityOverview(
  userId: string,
): Promise<SecurityOverview> {
  const [authData, auditData] = await Promise.all([
    apiFetch<{ authorizations: { data_type: string; authorized_agent: string; is_active: boolean; expires_at: string }[] }>(
      `/api/security/authorizations/${userId}`,
    ),
    apiFetch<{ logs: { action: string; agent: string; data_type: string; timestamp: string; detail: string }[] }>(
      `/api/security/audit-log/${userId}`,
    ),
  ]);

  if (authData || auditData) {
    // 将后端数据映射到前端结构
    const overview = { ...mockSecurityOverview };

    if (authData?.authorizations) {
      overview.active_authorizations = authData.authorizations.filter(
        (a) => a.is_active,
      ).length;
    }

    if (auditData?.logs) {
      overview.audit_log = auditData.logs.map((log) => ({
        time: log.timestamp.replace("T", " ").slice(0, 16),
        agent: log.agent,
        action: log.detail || log.action,
        dataType: log.data_type,
        status: "allowed" as const,
      }));
      overview.today_accesses = overview.audit_log.length;
    }

    return overview;
  }

  return mockSecurityOverview;
}

/** 更新授权 */
export async function updateAuthorization(
  authData: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const data = await apiFetch<Record<string, unknown>>(
    "/api/security/authorize",
    {
      method: "POST",
      body: JSON.stringify(authData),
    },
  );
  if (data) return data;
  // 降级：返回模拟成功响应
  return { success: true, message: "授权更新成功（模拟）" };
}

// ==================== P2 新增端点 ====================

export interface ProactiveAlert {
  level: "high" | "medium" | "low";
  icon: string;
  title: string;
  description?: string;
  desc?: string;
  suggestion?: string;
  action?: string;
  evidence?: Array<Record<string, unknown>>;
  timestamp?: string;
}

/** 主动健康预警（用户登录触发，体现主动式服务） */
export async function getProactiveAlerts(
  userId: string,
): Promise<ProactiveAlert[]> {
  const data = await apiFetch<{ alerts: ProactiveAlert[]; alert_count: number }>(
    `/api/health/${userId}/proactive-alerts`,
  );
  if (data?.alerts) return data.alerts;
  return [];
}

/** 复合意图对话（多 Agent 协作） */
export async function sendComplexChat(
  req: ChatRequest,
): Promise<ChatResponse & { agents_invoked?: string[]; multi_agent?: boolean; intent_weights?: Array<{ intent: string; weight: number }> }> {
  const data = await apiFetch<
    ChatResponse & { agents_invoked?: string[]; multi_agent?: boolean; intent_weights?: Array<{ intent: string; weight: number }> }
  >("/api/agents/complex-chat", {
    method: "POST",
    body: JSON.stringify(req),
  });
  if (data) return data;
  // 降级到普通 chat
  return sendChatMessage(req);
}

/** 数据安全：获取所有用户（用户切换器用） */
export async function getUsers(): Promise<Array<{ id: number; name: string; age: number; gender: string; city: string; insurance_type: string; employee_status: string }>> {
  const data = await apiFetch<{ users: Array<Record<string, unknown>> }>("/api/users");
  if (data?.users) {
    return data.users as never;
  }
  return [];
}

/** 可信数据空间数据流转记录（P2-2 可视化用） */
export async function getDataFlow(userId: string): Promise<{
  user_name: string;
  total_flows: number;
  flows: Array<{
    id: string;
    data_type: string;
    agent: string;
    steps: Array<{ step: string; actor: string; status: string; detail: string; ts: string }>;
  }>;
  principle: string;
} | null> {
  return apiFetch(`/api/security/data-flow/${userId}`);
}

// ==================== EEG 脑电健康（BCI×医保创新） ====================

/** 获取支持的心理状态列表 */
export async function getEEGMentalStates(): Promise<EEGMentalState[]> {
  const data = await apiFetch<{ states: EEGMentalState[] }>(`/api/eeg/states`);
  if (data?.states) return data.states;
  return [
    { key: "relaxed", label: "放松", stress: 20, attention: 50, sleep: 85, cognitive: 30 },
    { key: "focused", label: "专注", stress: 40, attention: 88, sleep: 65, cognitive: 75 },
    { key: "stressed", label: "高压力", stress: 85, attention: 60, sleep: 45, cognitive: 80 },
    { key: "fatigued", label: "疲劳", stress: 50, attention: 30, sleep: 40, cognitive: 35 },
    { key: "sleep_deprived", label: "睡眠不足", stress: 60, attention: 35, sleep: 25, cognitive: 40 },
  ];
}

/** 发起一次 EEG 采集会话 */
export async function createEEGSession(
  userId: string,
  mentalState: string = "auto",
  durationSeconds: number = 4,
): Promise<EEGSession | null> {
  const data = await apiFetch<EEGSession>(
    `/api/eeg/${userId}/session?mental_state=${encodeURIComponent(mentalState)}&duration_seconds=${durationSeconds}`,
    { method: "POST" },
  );
  return data;
}

/** 获取最近一次 EEG 评估 */
export async function getLatestEEG(userId: string): Promise<EEGSession | null> {
  const data = await apiFetch<EEGSession>(`/api/eeg/${userId}/latest`);
  return data;
}

/** 获取 EEG 历史趋势 */
export async function getEEGHistory(userId: string, limit: number = 20): Promise<EEGHistory | null> {
  const data = await apiFetch<EEGHistory>(`/api/eeg/${userId}/history?limit=${limit}`);
  return data;
}

/** 获取实时 EEG 数据块（前端轮询模拟实时采集） */
export async function getEEGRealtime(
  userId: string,
  mentalState: string = "relaxed",
  seed: number = 0,
): Promise<EEGRealtimeChunk | null> {
  const data = await apiFetch<EEGRealtimeChunk>(
    `/api/eeg/${userId}/realtime?mental_state=${encodeURIComponent(mentalState)}&seed=${seed}`,
  );
  return data;
}

/** 获取脑电异常 → 医保政策联动推荐 */
export async function getEEGPolicyLinks(
  userId: string,
): Promise<{ policy_links: EEGPolicyLink[]; summary: string; mental_state_label: string } | null> {
  const data = await apiFetch<{ policy_links: EEGPolicyLink[]; summary: string; mental_state_label: string }>(
    `/api/eeg/${userId}/policy-links`,
  );
  return data;
}

// ---- 真实 EEG 设备接入（LSL / 文件导入） ----

/** LSL EEG 设备连接状态 */
export interface EEGDeviceStatus {
  connected: boolean;
  stream_count: number;
  streams: Array<{
    name: string;
    type: string;
    channel_count: number;
    nominal_srate: number;
    source_id?: string;
  }>;
  pylsl_installed: boolean;
  message: string;
}

/** 检查 LSL EEG 设备连接状态 */
export async function checkEEGDevice(): Promise<EEGDeviceStatus | null> {
  return apiFetch<EEGDeviceStatus>(`/api/eeg/device/check`);
}

/** 从真实 EEG 设备（LSL 流）发起采集会话 */
export async function createEEGSessionFromDevice(
  userId: string,
  durationSeconds: number = 4,
  mentalState: string = "auto",
): Promise<EEGSession | null> {
  const data = await apiFetch<EEGSession>(
    `/api/eeg/${userId}/session-device?duration_seconds=${durationSeconds}&mental_state=${encodeURIComponent(mentalState)}`,
    { method: "POST" },
  );
  return data;
}

/** 导入 EEG 文件（CSV/EDF/TXT）并分析 */
export async function importEEGFile(
  userId: string,
  file: File,
  sampleRate: number = 256,
  mentalState: string = "auto",
): Promise<EEGSession | null> {
  try {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/api/eeg/${userId}/import?sample_rate=${sampleRate}&mental_state=${encodeURIComponent(mentalState)}`,
      {
        method: "POST",
        body: form,
        signal: AbortSignal.timeout(120000),
      },
    );
    if (!res.ok) return null;
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return (await res.json()) as EEGSession;
  } catch {
    return null;
  }
}

// ==================== 医学影像 AI 标注（影像卫士） ====================

export interface ImagingAnnotation {
  action: "confirm" | "reject" | "add" | "update";
  index?: number;
  finding_type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  confidence: number;
  severity: string;
  evidence?: string;
}

export interface ImagingReviewResult {
  record_id: number;
  final_findings: ImagingFindingItem[];
  report: ImagingReportData;
  policy_links: ImagingPolicyLink[];
}

/** 获取支持的影像检查类型与病灶类别 */
export async function getImagingStudyTypes(): Promise<Record<string, ImagingStudyTypeInfo> | null> {
  const data = await apiFetch<{ study_types: Record<string, ImagingStudyTypeInfo> }>(
    "/api/imaging/study-types",
  );
  if (data?.study_types) return data.study_types;
  return mockImagingStudyTypes;
}

/** 发起一次影像 AI 分析（合成影像 → 病灶检测 → AI 预标注） */
export async function analyzeImaging(
  userId: string,
  studyType: string,
  findingsKeys?: string[],
  seed?: number,
): Promise<ImagingStudyResponse | null> {
  const data = await apiFetch<ImagingStudyResponse>(`/api/imaging/${userId}/analyze`, {
    method: "POST",
    body: JSON.stringify({
      study_type: studyType,
      findings_keys: findingsKeys,
      seed,
    }),
  });
  if (data) return data;
  // 降级：返回模拟影像（仅当类型匹配时；否则按类型生成简化版）
  if (studyType !== mockImagingStudy.study_type) {
    return {
      ...mockImagingStudy,
      study_type: studyType,
      study_label: mockImagingStudyTypes[studyType]?.label || studyType,
    };
  }
  return mockImagingStudy;
}

/** 医生复核：提交 AI 标注确认/驳回/新增/修正 */
export async function reviewImaging(
  userId: string,
  recordId: number,
  annotations: ImagingAnnotation[],
): Promise<ImagingReviewResult | null> {
  const data = await apiFetch<ImagingReviewResult>(
    `/api/imaging/${userId}/records/${recordId}/review`,
    {
      method: "POST",
      body: JSON.stringify({ annotations }),
    },
  );
  if (data) return data;
  // 降级：基于本地 findings 计算最终结果
  const base = mockImagingStudy;
  const ops = new Map<number, ImagingAnnotation>();
  annotations.forEach((a, i) => ops.set(i, a));
  const finalFindings: ImagingFindingItem[] = [];
  base.findings.forEach((f, i) => {
    if (!ops.has(i) || ops.get(i)!.action === "confirm") {
      finalFindings.push({ ...f, status: "confirmed" });
    }
  });
  for (const a of annotations.filter((x) => x.action === "add")) {
    finalFindings.push({
      finding_type: a.finding_type,
      label: a.finding_type,
      x: a.x,
      y: a.y,
      w: a.w,
      h: a.h,
      confidence: a.confidence,
      severity: (a.severity as "low" | "medium" | "high") || "medium",
      source: "doctor",
      status: "confirmed",
      evidence: a.evidence,
    });
  }
  return {
    record_id: recordId,
    final_findings: finalFindings,
    report: {
      conclusion: `医师复核完成，共确认 ${finalFindings.length} 处发现。`,
      risk_level: finalFindings.some((f) => f.severity === "high") ? "高风险" : "中风险",
      advice: ["请结合临床资料综合评估", "必要时完善进一步检查"],
      confirmed_count: finalFindings.length,
      pending_count: 0,
      rejected_count: annotations.filter((a) => a.action === "reject").length,
      generated_at: new Date().toISOString(),
      disclaimer: base.disclaimer,
    },
    policy_links: mockImagingPolicyLinks,
  };
}

/** 获取用户影像检查历史 */
export async function getImagingRecords(
  userId: string,
  limit: number = 10,
): Promise<ImagingRecordItem[] | null> {
  const data = await apiFetch<{ records: ImagingRecordItem[] }>(
    `/api/imaging/${userId}/records?limit=${limit}`,
  );
  if (data?.records) return data.records;
  return mockImagingRecords;
}
