"use client";

import { useState, useRef, useEffect } from "react";
import { ChatInput } from "@/components/chat-input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Shield, Heart, FileText, BookOpen, Bot, User, Paperclip, Sparkles, Loader2, Brain, Pill, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { sendChatMessage, sendComplexChat, uploadBodyDocument, prereviewUploaded, scanDrug, registerDrug, type BodyUploadResult, type DrugInfo } from "@/lib/api";
import { useUser } from "@/lib/user-context";
import { ProactiveAlertBanner } from "@/components/proactive-alert-banner";
import { EvidencePanel, type Evidence } from "@/components/evidence-panel";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  agent?: string;
  agentColor?: string;
  timestamp: string;
  isLoading?: boolean;
  error?: boolean;
  evidence?: Evidence[];
  userProfile?: { name?: string; age?: number; insurance_type?: string; chronic_diseases?: string[] } | null;
  // 上传附件预览：图片显示缩略图，其余显示文件卡片，保证资料在对话流中可见
  attachment?: { name: string; url: string; isImage: boolean };
  // P2-1 多智能体协作展示
  multiAgent?: boolean;
  agentsInvoked?: string[];
  // 药品识别结果：携带待确认药品，气泡内渲染「加入用药记录」决策按钮（仅识别成功时）
  drugScan?: { drug: DrugInfo; category?: string };
  drugScanDecided?: boolean;
}

const quickActions = [
  { icon: Shield, label: "查看我的医保权益", prompt: "帮我查看我的医保权益", color: "bg-blue-500/10 text-blue-600" },
  { icon: FileText, label: "报销预审", prompt: "帮我预审报销材料", color: "bg-orange-500/10 text-orange-600" },
  { icon: Heart, label: "健康风险评估", prompt: "帮我做健康风险评估", color: "bg-green-500/10 text-green-600" },
  { icon: Brain, label: "脑电健康评估", prompt: "帮我做脑电健康评估", color: "bg-purple-500/10 text-purple-600" },
  { icon: BookOpen, label: "政策匹配查询", prompt: "帮我查询匹配的医保政策", color: "bg-indigo-500/10 text-indigo-600" },
  // 第 6 个入口：打开药品照片选择器，识别结果进入对话流（第 11 步）
  { icon: Pill, label: "药品识别", prompt: "", id: "drug-scan", color: "bg-emerald-500/10 text-emerald-600" },
];

const agentColorMap: Record<string, string> = {
  coverage_agent: "bg-blue-100 text-blue-700",
  claims_agent: "bg-orange-100 text-orange-700",
  health_agent: "bg-green-100 text-green-700",
  policy_agent: "bg-purple-100 text-purple-700",
  security_agent: "bg-cyan-100 text-cyan-700",
  eeg_agent: "bg-fuchsia-100 text-fuchsia-700",
  body_agent: "bg-teal-100 text-teal-700",
  drug_agent: "bg-emerald-100 text-emerald-700",
  orchestrator_agent: "bg-gradient-to-r from-blue-500 to-purple-500 text-white",
  "权益管家": "bg-blue-100 text-blue-700",
  "报销助手": "bg-orange-100 text-orange-700",
  "健康卫士": "bg-green-100 text-green-700",
  "政策顾问": "bg-purple-100 text-purple-700",
  "脑电卫士": "bg-fuchsia-100 text-fuchsia-700",
  "档案管家": "bg-teal-100 text-teal-700",
  "药品卫士": "bg-emerald-100 text-emerald-700",
};

const agentLabelMap: Record<string, string> = {
  coverage_agent: "权益管家",
  claims_agent: "报销助手",
  health_agent: "健康卫士",
  policy_agent: "政策参谋",
  security_agent: "安全守门",
  eeg_agent: "脑电卫士",
  body_agent: "档案管家",
  drug_agent: "药品卫士",
  orchestrator_agent: "编排智能体",
};

/**
 * 多意图检测：轻量关键词组合判定，命中则走多智能体协作端点。
 * 单意图/纯闲聊走普通 chat。规则参考 orchestrator.multi_intent_recognition。
 */
const INTENT_KEYWORDS: Array<{ intents: string[]; words: string[] }> = [
  // 报销/费用 + 政策/省钱
  { intents: ["claims", "policy"], words: ["报销", "能报", "花多少", "报多少", "自费", "费用"] },
  // 权益/账户 + 健康/用药
  { intents: ["coverage", "health_profile"], words: ["权益", "账户", "余额", "卡里", "医保卡", "统筹"] },
  // 政策 + 健康（慢病专项）
  { intents: ["policy", "health_profile"], words: ["政策", "补贴", "省钱", "福利", "待遇", "专项"] },
  // 脑电 + 政策（BCI×医保联动）
  { intents: ["eeg", "policy"], words: ["脑电", "压力", "睡眠", "注意力", "情绪", "心理"] },
];

function detectMultiIntent(message: string): boolean {
  const text = message.toLowerCase();
  const hits: Record<string, boolean> = {};
  for (const group of INTENT_KEYWORDS) {
    if (group.words.some((w) => text.includes(w))) {
      group.intents.forEach((i) => (hits[i] = true));
    }
  }
  // 命中 ≥2 个不同意图域才认为是复合意图
  return Object.keys(hits).length >= 2;
}

export default function HomePage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 药品卫士：专用照片选择器（识别结果进入对话流，不再是弹层面板）
  const drugInputRef = useRef<HTMLInputElement>(null);
  // 对话历史缓冲（发给后端做上下文连续性/指代消解）与报销流程活跃标记
  const historyRef = useRef<Array<{ role: string; content: string }>>([]);
  const claimsFlowRef = useRef(false);
  const { userId, currentUser } = useUser();

  const pushHistory = (role: "user" | "assistant", content: string) => {
    const h = historyRef.current;
    h.push({ role, content: content.slice(0, 200) });
    if (h.length > 8) h.splice(0, h.length - 8);
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (content: string) => {
    if (isSending) return;

    const history = [...historyRef.current];
    pushHistory("user", content);

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((prev) => [...prev, userMsg]);

    const loadingId = (Date.now() + 1).toString();
    const loadingMsg: Message = {
      id: loadingId,
      role: "assistant",
      content: "",
      agent: "MedSignal",
      agentColor: "bg-blue-100 text-blue-700",
      timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
      isLoading: true,
    };
    setMessages((prev) => [...prev, loadingMsg]);
    setIsSending(true);

    try {
      // P2-1：复合意图走多智能体协作，单意图走普通 chat
      const isMulti = detectMultiIntent(content);
      const res = isMulti
        ? await sendComplexChat({ message: content, user_id: userId, history })
        : await sendChatMessage({ message: content, user_id: userId, history });

      const agentsInvoked = isMulti
        ? (((res as unknown as Record<string, unknown>).agents_invoked as string[]) ?? []).map((a: string) => agentLabelMap[a] || a)
        : undefined;

      const assistantMsg: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        content: res.response,
        agent: isMulti
          ? "编排智能体"
          : agentLabelMap[res.agent_type] || res.agent_type,
        agentColor: agentColorMap[res.agent_type] || "bg-blue-100 text-blue-700",
        timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
        evidence: res.evidence as Evidence[] | undefined,
        userProfile: res.user_profile,
        multiAgent: isMulti && (((res as unknown as Record<string, unknown>).multi_agent as boolean) || (agentsInvoked?.length ?? 0) > 0),
        agentsInvoked: agentsInvoked && agentsInvoked.length > 0 ? agentsInvoked : undefined,
      };

      setMessages((prev) => prev.map((m) => (m.id === loadingId ? assistantMsg : m)));
      pushHistory("assistant", res.response);
      // 报销流程活跃标记：用户发起预审/报销，或响应来自报销助手
      if (
        /预审|报销|理赔/.test(content) ||
        (res.agent_type || "").includes("claims") ||
        (agentsInvoked ?? []).some((a) => a.includes("报销"))
      ) {
        claimsFlowRef.current = true;
      }
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        content: "抱歉，处理您的请求时出现了问题，请稍后重试。",
        agent: "MedSignal",
        agentColor: "bg-blue-100 text-blue-700",
        timestamp: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
        error: true,
      };

      setMessages((prev) => prev.map((m) => (m.id === loadingId ? errorMsg : m)));
    } finally {
      setIsSending(false);
    }
  };

  const handleRetry = (msgId: string, originalContent: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== msgId));
    handleSend(originalContent);
  };

  /** 回形针上传医疗资料（支持多文件）→ 档案管家（/api/body/{user_id}/upload）转录归档 */
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // 允许重复选择同一文件
    if (files.length === 0 || isSending) return;

    const ts = () => new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    const MAX_SIZE = 10 * 1024 * 1024;
    const valid = files.filter((f) => f.size <= MAX_SIZE);
    const oversized = files.filter((f) => f.size > MAX_SIZE);

    // 每个文件一条用户气泡，附件预览在对话中可见
    if (valid.length > 0) {
      const base = Date.now();
      valid.forEach((f) => pushHistory("user", `[上传了《${f.name}》]`));
      setMessages((prev) => [
        ...prev,
        ...valid.map(
          (file, i): Message => ({
            id: `${base}-${i}`,
            role: "user",
            content: `📎 上传医疗资料：${file.name}`,
            timestamp: ts(),
            attachment: {
              name: file.name,
              url: URL.createObjectURL(file),
              isImage: file.type.startsWith("image/"),
            },
          }),
        ),
      ]);
    }

    // 超大文件单独提示，不阻塞其余文件
    if (oversized.length > 0) {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-oversize`,
          role: "assistant",
          content: `以下文件超过 10MB 限制，未上传：${oversized.map((f) => f.name).join("、")}`,
          agent: "档案管家",
          agentColor: agentColorMap["档案管家"],
          timestamp: ts(),
          error: true,
        },
      ]);
    }

    if (valid.length === 0) return;

    const loadingId = `${Date.now()}-loading`;
    setMessages((prev) => [
      ...prev,
      {
        id: loadingId,
        role: "assistant",
        content: "",
        agent: "档案管家",
        agentColor: agentColorMap["档案管家"],
        timestamp: ts(),
        isLoading: true,
      },
    ]);
    setIsSending(true);

    try {
      // 后端为单文件接口，多文件顺序上传后汇总为一条回复
      const results: Array<{ file: File; res: BodyUploadResult | null }> = [];
      for (const file of valid) {
        results.push({ file, res: await uploadBodyDocument(userId, file) });
      }
      const okCount = results.filter((r) => r.res !== null).length;

      let content: string;
      let isError = false;
      if (okCount === 0) {
        content = "抱歉，资料上传失败，请稍后重试。";
        isError = true;
      } else if (results.length === 1) {
        // 单文件沿用完整智能体回复
        content = results[0].res?.agent_response || "已收到您的资料并完成归档。";
      } else {
        content =
          `已处理 ${results.length} 份资料（成功 ${okCount} 份）：\n` +
          results
            .map((r) =>
              r.res
                ? `✅ 《${r.file.name}》（${r.res.doc_kind}）已存档，新增 ${r.res.records_added} 条记录`
                : `❌ 《${r.file.name}》上传失败，请稍后重试`,
            )
            .join("\n");
      }

      const assistantMsgBase: Message = {
        id: `${Date.now()}-done`,
        role: "assistant",
        content,
        agent: "档案管家",
        agentColor: agentColorMap["档案管家"],
        timestamp: ts(),
        error: isError,
      };

      // 报销流程活跃：编排智能体 调度 档案管家×报销助手 对已上传资料联合预审
      let assistantMsg = assistantMsgBase;
      if (claimsFlowRef.current && okCount > 0) {
        const pr = await prereviewUploaded(userId);
        if (pr) {
          assistantMsg = {
            id: `${Date.now()}-done`,
            role: "assistant",
            content: pr.response,
            agent: "编排智能体",
            agentColor: agentColorMap["orchestrator_agent"],
            timestamp: ts(),
            multiAgent: pr.multi_agent,
            agentsInvoked: pr.multi_agent
              ? pr.agents_invoked.map((a) => agentLabelMap[a] || a)
              : undefined,
          };
        }
      }

      pushHistory("assistant", assistantMsg.content);
      setMessages((prev) => prev.map((m) => (m.id === loadingId ? assistantMsg : m)));
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== loadingId));
    } finally {
      setIsSending(false);
    }
  };

  const showWelcome = messages.length === 0;

  /** 药品卫士：选择药盒照片 → 预览气泡 → 识别 → 结果进入对话流（是否登记由用户决定） */
  const handleDrugScan = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || isSending) return;

    const ts = () => new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    if (file.size > 10 * 1024 * 1024) {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-oversize`,
          role: "assistant",
          content: "文件大小超过 10MB 限制，请压缩后重新上传",
          agent: "药品卫士",
          agentColor: agentColorMap["药品卫士"],
          timestamp: ts(),
          error: true,
        },
      ]);
      return;
    }

    // 用户气泡：图片预览在对话中可见（第 7 步）
    pushHistory("user", `[上传了药品照片《${file.name}》]`);
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-drug`,
        role: "user",
        content: `📷 识别药品：${file.name}`,
        timestamp: ts(),
        attachment: {
          name: file.name,
          url: URL.createObjectURL(file),
          isImage: true,
        },
      },
    ]);

    // 药品卫士思考中气泡（第 8 步）
    const loadingId = `${Date.now()}-drug-loading`;
    setMessages((prev) => [
      ...prev,
      {
        id: loadingId,
        role: "assistant",
        content: "",
        agent: "药品卫士",
        agentColor: agentColorMap["药品卫士"],
        timestamp: ts(),
        isLoading: true,
      },
    ]);
    setIsSending(true);

    try {
      const res = await scanDrug(userId, file);
      if (!res) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingId
              ? { ...m, content: "识别服务暂不可用，请稍后重试", isLoading: false, error: true }
              : m,
          ),
        );
        return;
      }

      // 识别结果气泡：后端 chat_response 已含【药品卫士】署名与完整信息（第 9 步）
      const content =
        res.chat_response ||
        (res.not_a_drug
          ? "这张图片看起来不是药品包装，请上传药盒、药品包装或说明书的清晰照片。"
          : "未能识别出药品信息，请更换更清晰的照片重试。");
      const assistantMsg: Message = {
        id: `${Date.now()}-drug-done`,
        role: "assistant",
        content,
        agent: "药品卫士",
        agentColor: agentColorMap["药品卫士"],
        timestamp: ts(),
        // 识别成功且非「不是药品」时才提供登记入口（第 11 步）
        drugScan: !res.not_a_drug && res.drug ? { drug: res.drug, category: res.category } : undefined,
      };
      pushHistory("assistant", assistantMsg.content);
      setMessages((prev) => prev.map((m) => (m.id === loadingId ? assistantMsg : m)));
    } catch {
      setMessages((prev) => prev.filter((m) => m.id !== loadingId));
    } finally {
      setIsSending(false);
    }
  };

  /** 识别结果气泡内的决策：加入用药记录 / 暂不添加（未点击前绝不写库） */
  const handleDrugDecision = async (msgId: string, accept: boolean) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg?.drugScan || msg.drugScanDecided) return;
    const ts = () => new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });

    // 立即收起按钮，防止重复提交；结果以新气泡呈现，保持对话流连贯（第 12 步）
    setMessages((prev) => prev.map((m) => (m.id === msgId ? { ...m, drugScanDecided: true } : m)));

    let content: string;
    let isError = false;
    if (accept) {
      const res = await registerDrug(userId, msg.drugScan.drug, msg.drugScan.category);
      if (res?.registered) {
        content = res.message;
        pushHistory("assistant", content);
      } else {
        content = res?.message || "登记失败，请稍后重试";
        isError = !res;
      }
    } else {
      content = "好的，已跳过登记，不会写入用药记录。如需后续添加，可再次拍照识别。";
      pushHistory("assistant", content);
    }

    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-drug-confirm`,
        role: "assistant",
        content,
        agent: "药品卫士",
        agentColor: agentColorMap["药品卫士"],
        timestamp: ts(),
        error: isError,
      },
    ]);
  };

  /** 快捷入口：药品识别打开照片选择器，其余走聊天 */
  const handleQuickAction = (action: { prompt: string; id?: string }) => {
    if (action.id === "drug-scan") {
      drugInputRef.current?.click();
      return;
    }
    handleSend(action.prompt);
  };

  return (
    <div className="flex h-screen flex-col bg-gradient-to-b from-background to-background/80">
      {/* Header */}
      <header className="border-b border-border/50 bg-white/80 backdrop-blur-sm px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg shadow-blue-500/20">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-foreground">MedSignal</h1>
              <p className="text-xs text-muted-foreground">多模态医疗信号智能体 · 关键医疗信号识别 × 患者信息连接</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
              在线
            </Badge>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {/* 主动健康预警横幅（P2-3 范式创新） */}
          <ProactiveAlertBanner />

          <AnimatePresence mode="popLayout">
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <ChatBubble message={msg} onRetry={handleRetry} previousUserMessage={getPreviousUserMessage(messages, msg.id)} onDrugDecision={handleDrugDecision} />
              </motion.div>
            ))}
          </AnimatePresence>

          {showWelcome && (
            <WelcomeScreen
              onAction={handleQuickAction}
              userName={currentUser.name}
              userConditions={currentUser.conditions}
            />
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-border/50 bg-white/80 backdrop-blur-sm px-6 py-4">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-center gap-2 rounded-2xl border border-border bg-white px-4 py-2 shadow-sm transition-shadow focus-within:shadow-md focus-within:border-primary/30">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="image/*,application/pdf,text/plain"
              className="hidden"
              onChange={handleFileUpload}
            />
            <input
              ref={drugInputRef}
              type="file"
              accept="image/jpeg,image/png"
              className="hidden"
              onChange={handleDrugScan}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isSending}
              title="上传医疗资料（可多选）"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors disabled:opacity-50"
            >
              <Paperclip className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => drugInputRef.current?.click()}
              disabled={isSending}
              title="药品识别：拍摄或选择药盒照片"
              className="flex h-8 w-8 items-center justify-center rounded-lg text-emerald-600/70 hover:bg-emerald-50 hover:text-emerald-600 transition-colors disabled:opacity-50"
            >
              <Pill className="h-4 w-4" />
            </button>
            <ChatInput onSend={handleSend} placeholder={`为 ${currentUser.name} 识别关键医疗信号、解答医保与健康问题...`} disabled={isSending} />
          </div>
          <div className="mt-2 flex items-center gap-2 px-2">
            <Badge variant="secondary" className="text-xs">
              AI 助手
            </Badge>
            <span className="text-xs text-muted-foreground">
              回答仅供参考，具体以医保政策为准
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function getPreviousUserMessage(messages: Message[], currentId: string): string {
  const idx = messages.findIndex((m) => m.id === currentId);
  for (let i = idx - 1; i >= 0; i--) {
    if (messages[i].role === "user") return messages[i].content;
  }
  return "";
}

function ChatBubble({ message, onRetry, previousUserMessage, onDrugDecision }: { message: Message; onRetry: (id: string, content: string) => void; previousUserMessage: string; onDrugDecision: (msgId: string, accept: boolean) => void }) {
  const isUser = message.role === "user";

  if (message.isLoading) {
    return (
      <div className="flex gap-3">
        <Avatar className="h-8 w-8 shrink-0 mt-1">
          <AvatarFallback className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
            <Bot className="h-4 w-4" />
          </AvatarFallback>
        </Avatar>
        <div className="max-w-[75%] flex flex-col gap-1 items-start">
          <Badge variant="secondary" className={`text-xs w-fit ${message.agentColor || ""}`}>
            {message.agent}
          </Badge>
          <div className="rounded-2xl rounded-tl-sm px-4 py-2.5 bg-white border border-border shadow-sm flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
            <span className="text-sm text-muted-foreground">正在思考中...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <Avatar className="h-8 w-8 shrink-0 mt-1">
        <AvatarFallback
          className={
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-gradient-to-br from-blue-500 to-blue-600 text-white"
          }
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        {!isUser && message.agent && (
          <Badge
            variant="secondary"
            className={`text-xs w-fit ${message.agentColor || ""}`}
          >
            {message.agent}
          </Badge>
        )}
        {/* P2-1 多智能体协作徽章 */}
        {!isUser && message.multiAgent && message.agentsInvoked && (
          <div className="flex flex-wrap items-center gap-1">
            <Badge className="text-xs gap-1 bg-gradient-to-r from-blue-500 to-purple-500 text-white">
              <Sparkles className="h-3 w-3" />
              已调度 {message.agentsInvoked.length} 个智能体协同
            </Badge>
            {message.agentsInvoked.map((a) => (
              <Badge key={a} variant="outline" className="text-xs">
                {a}
              </Badge>
            ))}
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-line ${
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-sm"
              : message.error
              ? "bg-red-50 text-red-700 border border-red-200 rounded-tl-sm"
              : "bg-white text-card-foreground border border-border shadow-sm rounded-tl-sm"
          }`}
        >
          {/* 上传附件在对话气泡内可见：图片缩略图 / 文件卡片 */}
          {message.attachment &&
            (message.attachment.isImage ? (
              <div className="mb-2 overflow-hidden rounded-lg bg-white p-1">
                <img
                  src={message.attachment.url}
                  alt={message.attachment.name}
                  className="max-h-56 w-full rounded-md object-contain"
                />
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-lg bg-white/15 px-3 py-2">
                <FileText className="h-4 w-4 shrink-0" />
                <span className="truncate text-xs">{message.attachment.name}</span>
              </div>
            ))}
          {(!message.attachment || message.attachment.isImage) && message.content}
          {/* P2-4 可解释性追溯：AI 回答下方附证据面板 */}
          {!isUser && !message.error && (
            <EvidencePanel evidence={message.evidence} />
          )}
          {/* 药品识别决策按钮：仅在未决策时呈现，点击后才写用药记录 */}
          {!isUser && message.drugScan && !message.drugScanDecided && (
            <div className="mt-2 flex gap-2 border-t border-border pt-2">
              <button
                onClick={() => onDrugDecision(message.id, true)}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-emerald-700"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                加入用药记录
              </button>
              <button
                onClick={() => onDrugDecision(message.id, false)}
                className="flex items-center justify-center rounded-lg border border-border bg-white px-3 py-1.5 text-xs font-medium text-foreground transition-colors hover:bg-muted"
              >
                暂不添加
              </button>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground px-1">{message.timestamp}</span>
          {message.error && (
            <button
              onClick={() => onRetry(message.id, previousUserMessage)}
              className="text-xs text-red-500 hover:text-red-700 underline"
            >
              重试
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onAction, userName, userConditions }: { onAction: (action: { prompt: string; id?: string }) => void; userName: string; userConditions: string[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="flex flex-col items-center py-8"
    >
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-xl shadow-blue-500/25 mb-4">
        <Sparkles className="h-8 w-8 text-white" />
      </div>
      <h2 className="text-2xl font-bold text-foreground mb-1">MedSignal</h2>
      <p className="text-muted-foreground mb-1">您好，{userName}！我是您的多模态医疗信号智能体</p>
      {userConditions.length > 0 && (
        <p className="text-xs text-orange-600 mb-6">
          已关注您的健康状况：{userConditions.join("、")}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3 w-full max-w-lg">
        {quickActions.map((action, i) => (
          <motion.button
            key={action.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.3 + i * 0.1 }}
            onClick={() => onAction(action)}
            className="flex items-center gap-3 rounded-xl border border-border bg-white p-4 text-left transition-all hover:shadow-md hover:border-primary/20 hover:-translate-y-0.5"
          >
            <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${action.color}`}>
              <action.icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">{action.label}</p>
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
}
