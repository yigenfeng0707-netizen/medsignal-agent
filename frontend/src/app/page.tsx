"use client";

import { useState, useRef, useEffect } from "react";
import { ChatInput } from "@/components/chat-input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Shield, Heart, FileText, BookOpen, Bot, User, Paperclip, Sparkles, Loader2, Brain } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { sendChatMessage, sendComplexChat } from "@/lib/api";
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
  // P2-1 多智能体协作展示
  multiAgent?: boolean;
  agentsInvoked?: string[];
}

const quickActions = [
  { icon: Shield, label: "查看我的医保权益", prompt: "帮我查看我的医保权益", color: "bg-blue-500/10 text-blue-600" },
  { icon: FileText, label: "报销预审", prompt: "帮我预审报销材料", color: "bg-orange-500/10 text-orange-600" },
  { icon: Heart, label: "健康风险评估", prompt: "帮我做健康风险评估", color: "bg-green-500/10 text-green-600" },
  { icon: Brain, label: "脑电健康评估", prompt: "帮我做脑电健康评估", color: "bg-purple-500/10 text-purple-600" },
  { icon: BookOpen, label: "政策匹配查询", prompt: "帮我查询匹配的医保政策", color: "bg-indigo-500/10 text-indigo-600" },
];

const agentColorMap: Record<string, string> = {
  coverage_agent: "bg-blue-100 text-blue-700",
  claims_agent: "bg-orange-100 text-orange-700",
  health_agent: "bg-green-100 text-green-700",
  policy_agent: "bg-purple-100 text-purple-700",
  security_agent: "bg-cyan-100 text-cyan-700",
  eeg_agent: "bg-fuchsia-100 text-fuchsia-700",
  orchestrator_agent: "bg-gradient-to-r from-blue-500 to-purple-500 text-white",
  "权益管家": "bg-blue-100 text-blue-700",
  "报销助手": "bg-orange-100 text-orange-700",
  "健康卫士": "bg-green-100 text-green-700",
  "政策顾问": "bg-purple-100 text-purple-700",
  "脑电卫士": "bg-fuchsia-100 text-fuchsia-700",
};

const agentLabelMap: Record<string, string> = {
  coverage_agent: "权益管家",
  claims_agent: "报销助手",
  health_agent: "健康卫士",
  policy_agent: "政策参谋",
  security_agent: "安全守门",
  eeg_agent: "脑电卫士",
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
  const { userId, currentUser } = useUser();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (content: string) => {
    if (isSending) return;

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
      agent: "医保智脑",
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
        ? await sendComplexChat({ message: content, user_id: userId })
        : await sendChatMessage({ message: content, user_id: userId });

      const agentsInvoked = isMulti
        ? (res.agents_invoked ?? []).map((a) => agentLabelMap[a] || a)
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
        multiAgent: isMulti && (res.multi_agent || (agentsInvoked?.length ?? 0) > 0),
        agentsInvoked: agentsInvoked && agentsInvoked.length > 0 ? agentsInvoked : undefined,
      };

      setMessages((prev) => prev.map((m) => (m.id === loadingId ? assistantMsg : m)));
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 2).toString(),
        role: "assistant",
        content: "抱歉，处理您的请求时出现了问题，请稍后重试。",
        agent: "医保智脑",
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

  const showWelcome = messages.length === 0;

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
              <h1 className="text-lg font-bold text-foreground">医保智脑</h1>
              <p className="text-xs text-muted-foreground">基于可信数据空间的个人医保智能体</p>
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
                <ChatBubble message={msg} onRetry={handleRetry} previousUserMessage={getPreviousUserMessage(messages, msg.id)} />
              </motion.div>
            ))}
          </AnimatePresence>

          {showWelcome && (
            <WelcomeScreen
              onAction={handleSend}
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
            <button className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors">
              <Paperclip className="h-4 w-4" />
            </button>
            <ChatInput onSend={handleSend} placeholder={`为 ${currentUser.name} 解答医保问题...`} disabled={isSending} />
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

function ChatBubble({ message, onRetry, previousUserMessage }: { message: Message; onRetry: (id: string, content: string) => void; previousUserMessage: string }) {
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
          {message.content}
          {/* P2-4 可解释性追溯：AI 回答下方附证据面板 */}
          {!isUser && !message.error && (
            <EvidencePanel evidence={message.evidence} />
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

function WelcomeScreen({ onAction, userName, userConditions }: { onAction: (prompt: string) => void; userName: string; userConditions: string[] }) {
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
      <h2 className="text-2xl font-bold text-foreground mb-1">医保智脑</h2>
      <p className="text-muted-foreground mb-1">您好，{userName}！我是您的 AI 医保管家</p>
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
            onClick={() => onAction(action.prompt)}
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
