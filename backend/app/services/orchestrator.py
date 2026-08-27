"""
医保智脑 - 智能体编排服务

增强版编排器，集成：
- LLMService：用于意图识别和对话生成
- KnowledgeBase：用于政策知识检索
- 降级机制：服务不可用时回退到关键词匹配和 mock 数据
"""

import logging
from typing import Any, Optional

from app.config import settings
from app.services.knowledge_base import KnowledgeBase, SearchResult
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class Orchestrator:
    """智能体编排服务：意图识别、路由分发、结果聚合

    优先使用 LLM 进行意图识别和对话生成，
    优先使用 KnowledgeBase 进行政策检索，
    服务不可用时自动降级到关键词匹配和 mock 数据。
    """

    # 关键词意图映射（降级方案）
    AGENT_KEYWORDS: dict[str, list[str]] = {
        "coverage": ["报销", "待遇", "报销比例", "起付线", "封顶线", "医保卡", "个人账户", "缴费",
                     "能报多少", "报多少", "账户余额", "参保", "权益"],
        "claims": ["理赔", "报销流程", "发票", "OCR", "上传", "预审", "报销材料",
                   "票据", "报销单", "提交报销"],
        "health_profile": ["健康", "体检", "画像", "慢病", "用药", "趋势", "预警",
                           "健康风险", "身体状况"],
        "policy": ["政策", "规定", "通知", "办法", "文件", "异地", "省钱",
                   "惠民", "享受什么", "能享受", "门诊慢病"],
        "security": ["授权", "隐私", "数据安全", "审计", "权限", "我的数据"],
        "eeg": ["脑电", "EEG", "压力", "睡眠质量", "注意力", "认知负荷", "情绪",
                "放松", "专注", "疲劳", "焦虑", "心理", "脑机", "BCI", "波形",
                "脑电健康", "脑电评估", "脑电分析"],
    }

    # Mock 数据（降级方案）
    MOCK_RESPONSES: dict[str, dict[str, Any]] = {
        "coverage": {
            "response": "根据您的参保信息，城镇职工医保门诊报销比例为70%，住院报销比例为85%。",
            "data": {"reimbursement_rate": 0.70, "deductible": 800},
        },
        "claims": {
            "response": "已为您启动理赔预审流程，请上传相关发票和病历材料。",
            "data": {"pre_review_status": "pending", "required_docs": ["发票原件", "处方复印件"]},
        },
        "health_profile": {
            "response": "您的健康画像已生成，综合健康评分70分，建议关注慢性病管理。",
            "data": {"health_score": 70, "chronic_diseases": ["高血压"]},
        },
        "policy": {
            "response": "为您匹配到2条相关政策，门诊统筹报销比例已提升至70%。",
            "data": {"matched_count": 2, "top_policy": "浙江省城镇职工基本医疗保险门诊统筹办法"},
        },
        "security": {
            "response": "您的数据授权状态正常，当前有2项有效授权。",
            "data": {"active_authorizations": 2},
        },
        "eeg": {
            "response": "已为您完成脑电健康评估。基于 EEG 五频段功率分析，当前压力指数、注意力、睡眠质量、认知负荷四维指标正常。脑电异常将自动联动医保政策推荐。",
            "data": {"mental_state": "relaxed", "stress_index": 20, "attention_index": 50},
        },
    }

    def __init__(self):
        """初始化编排器，懒加载 LLM 和知识库服务"""
        self._llm: Optional[LLMService] = None
        self._kb: Optional[KnowledgeBase] = None
        self._services_initialized = False

    async def initialize_services(self) -> None:
        """初始化 LLM 和知识库服务

        应在应用启动时调用。初始化失败不影响基本功能，
        会自动降级到关键词匹配和 mock 数据。
        """
        if self._services_initialized:
            return

        if settings.DEMO_OFFLINE:
            logger.info("DEMO_OFFLINE=1：跳过 LLM/知识库初始化，使用离线降级模式")
            self._llm = None
            self._kb = None
            self._services_initialized = True
            return

        # 初始化 LLM 服务（主力：商汤 SenseNova，备选：阿里云 DashScope）
        try:
            self._llm = LLMService(
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_BASE_URL,
                model=settings.LLM_MODEL,
                fallback_api_key=settings.DASHSCOPE_API_KEY,
                fallback_base_url=settings.DASHSCOPE_BASE_URL,
                fallback_model=settings.DASHSCOPE_MODEL,
            )
            if self._llm.is_available:
                logger.info("LLM 服务初始化成功")
            else:
                logger.warning("LLM 服务不可用，将使用关键词匹配降级方案")
                self._llm = None
        except Exception as e:
            logger.warning("LLM 服务初始化失败: %s，将使用降级方案", e)
            self._llm = None

        # 初始化知识库服务
        # P0-4 修复：embedding 改用 ChromaDB 默认 sentence-transformers 离线模型
        # 原配置用 SenseNova base_url + text-embedding-3-small（OpenAI 模型名），商汤不支持会静默降级
        # 离线模型更稳定，无网络依赖，杜绝现场演示 embedding API 失败风险
        try:
            self._kb = KnowledgeBase(
                embedding_api_key="",      # 留空 → 自动用 ChromaDB 默认嵌入
                embedding_base_url="",
                embedding_model="",
            )
            await self._kb.initialize(persist_dir=settings.CHROMA_PERSIST_DIR)
            stats = await self._kb.get_stats()
            if stats.get("total_chunks", 0) > 0:
                logger.info("知识库服务初始化成功，已有 %d 个文本块", stats["total_chunks"])
            else:
                logger.warning("知识库为空，请先运行 build_knowledge_base.py 构建索引")
        except Exception as e:
            logger.warning("知识库服务初始化失败: %s，将使用 mock 数据降级方案", e)
            self._kb = None

        self._services_initialized = True

    # ------------------------------------------------------------------
    # 意图识别
    # ------------------------------------------------------------------

    async def intent_recognition(self, message: str) -> str:
        """根据用户消息识别意图，返回对应的智能体类型

        优先使用 LLM 进行意图识别，不可用时降级到关键词匹配。
        """
        # 优先使用 LLM
        if self._llm is not None:
            try:
                intent_result = await self._llm.extract_intent(message)
                intent = intent_result.get("intent", "")
                confidence = intent_result.get("confidence", 0)

                # 置信度足够高时使用 LLM 结果
                if intent in self.AGENT_KEYWORDS and confidence >= 0.5:
                    logger.info("LLM 意图识别: %s (confidence=%.2f)", intent, confidence)
                    return intent

                logger.info("LLM 意图置信度不足 (%.2f)，降级到关键词匹配", confidence)
            except Exception as e:
                logger.warning("LLM 意图识别异常: %s，降级到关键词匹配", e)

        # 降级：关键词匹配
        return self._keyword_intent(message)

    def _keyword_intent(self, message: str) -> str:
        """基于关键词的意图识别（降级方案）"""
        scores: dict[str, int] = {}
        for agent_type, keywords in self.AGENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message)
            scores[agent_type] = score

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return "coverage"
        return best

    def multi_intent_recognition(self, message: str) -> list[tuple[str, float]]:
        """多意图识别：返回 [(intent, weight), ...]，按权重降序

        用于复合问题（如"我父亲做心脏搭桥能报多少"→ coverage + policy + claims）。
        规则：所有命中关键词数 >=1 的意图都返回，权重 = 命中数/总命中数。
        """
        scores: dict[str, int] = {}
        for agent_type, keywords in self.AGENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message)
            if score > 0:
                scores[agent_type] = score

        if not scores:
            return [("coverage", 1.0)]

        total = sum(scores.values())
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # 只保留权重 >= 0.2 的意图（避免噪音）
        result = [(intent, score / total) for intent, score in ranked if score / total >= 0.2]
        return result if result else [("coverage", 1.0)]

    async def handle_complex_query(
        self, message: str, user_id: str | None = None, user_profile: dict | None = None,
    ) -> dict[str, Any]:
        """处理复合意图查询：并行调度多 Agent + 结果融合

        这是 P2-1 多智能体协作的核心。例如：
        "我父亲做心脏搭桥能报多少，有哪些政策能省 钱" → coverage + policy + claims 并行
        """
        intents = self.multi_intent_recognition(message)
        logger.info("复合意图识别: %s", intents)

        # 单意图直接走 route_to_agent
        if len(intents) == 1:
            result = await self.route_to_agent(intents[0][0], message, user_id, user_profile)
            return {**result, "agents_invoked": [intents[0][0]], "multi_agent": False}

        # 多意图：并行调度（asyncio.gather）+ 单 Agent 超时保护
        # 修复 Render 免费套餐 60s 超时问题：每个 Agent 限制 20s，并行总耗时 ≤ 20s + 融合 20s
        import asyncio

        async def _run_one(intent: str, weight: float) -> tuple[str, "dict | None"]:
            try:
                r = await asyncio.wait_for(
                    self.route_to_agent(intent, message, user_id, user_profile),
                    timeout=20.0,
                )
                return intent, r
            except asyncio.TimeoutError:
                logger.warning("Agent %s 执行超时(20s)，跳过", intent)
                return intent, None
            except Exception as e:
                logger.error("Agent %s 执行失败: %s", intent, e)
                return intent, None

        tasks = [_run_one(intent, weight) for intent, weight in intents[:3]]
        gathered = await asyncio.gather(*tasks)
        agent_results: dict[str, dict] = {}
        for intent, r in gathered:
            if r is not None:
                agent_results[intent] = r

        # 若所有 Agent 都超时/失败，用兜底
        if not agent_results:
            return {
                "response": "抱歉，智能体处理超时，请稍后重试或简化您的问题。",
                "data": {"agents_invoked": [], "multi_agent": True, "timeout_fallback": True},
                "agents_invoked": [],
                "multi_agent": True,
                "intent_weights": [{"intent": i, "weight": round(w, 2)} for i, w in intents],
            }

        # 结果融合（带超时保护，超时降级到拼接）
        try:
            fused = await asyncio.wait_for(
                self._fuse_multi_agent_results(message, intents, agent_results),
                timeout=20.0,
            )
        except asyncio.TimeoutError:
            logger.warning("LLM 融合超时(20s)，降级拼接")
            fused = self._fuse_fallback(intents, agent_results)

        return {
            **fused,
            "agents_invoked": list(agent_results.keys()),
            "multi_agent": True,
            "intent_weights": [{"intent": i, "weight": round(w, 2)} for i, w in intents],
        }

    def _fuse_fallback(self, intents: list[tuple[str, float]],
                       agent_results: dict[str, dict]) -> dict[str, Any]:
        """LLM 融合超时时的降级拼接（不调 LLM，避免再次超时）"""
        agent_names = {
            "coverage": "权益管家", "claims": "报销助手",
            "health_profile": "健康卫士", "policy": "政策参谋",
            "security": "安全守门", "eeg": "脑电卫士",
        }
        parts = []
        for intent, result in agent_results.items():
            name = agent_names.get(intent, intent)
            resp = result.get("response", "")[:400]
            if resp:
                parts.append(f"**【{name}】**\n{resp}")
        return {
            "response": "\n\n---\n\n".join(parts) if parts else "暂无法处理该复合问题",
            "data": {"fused": False, "agent_count": len(agent_results), "fallback": True},
        }

    async def _fuse_multi_agent_results(
        self, message: str, intents: list[tuple[str, float]],
        agent_results: dict[str, dict],
    ) -> dict[str, Any]:
        """融合多 Agent 结果为一段连贯回答，标注来源 Agent。"""
        agent_names = {
            "coverage": "权益管家", "claims": "报销助手",
            "health_profile": "健康卫士", "policy": "政策参谋",
            "security": "安全守门", "eeg": "脑电卫士",
        }

        # 优先用 LLM 融合
        if self._llm is not None and agent_results:
            try:
                # 构建各 Agent 输出摘要
                agent_outputs = []
                for intent, result in agent_results.items():
                    name = agent_names.get(intent, intent)
                    resp = result.get("response", "")[:500]
                    agent_outputs.append(f"【{name}】{resp}")

                fusion_prompt = (
                    "你是医保智脑的编排智能体。以下是多个专业智能体对同一问题的回答，"
                    "请将它们融合成一段连贯、完整、不重复的回答。"
                    "保留各智能体的关键结论，用【智能体名】标注信息来源。"
                    "如果某些信息重复，合并表述。最后给出 1-2 条综合建议。"
                )
                fused = await self._llm.chat(
                    messages=[
                        {"role": "system", "content": fusion_prompt},
                        {"role": "user", "content": f"用户问题：{message}\n\n各智能体回答：\n\n" + "\n\n".join(agent_outputs)},
                    ],
                    temperature=0.4,
                )
                return {
                    "response": fused,
                    "data": {"fused": True, "agent_count": len(agent_results)},
                    "evidence": [
                        {"type": "agent_source", "agent": agent_names.get(i, i), "weight": round(w, 2)}
                        for i, w in intents if i in agent_results
                    ],
                }
            except Exception as e:
                logger.error("LLM 融合失败: %s，降级拼接", e)

        # 降级：直接拼接各 Agent 回答
        parts = []
        for intent, result in agent_results.items():
            name = agent_names.get(intent, intent)
            resp = result.get("response", "")
            if resp:
                parts.append(f"**【{name}】**\n{resp}")
        return {
            "response": "\n\n---\n\n".join(parts) if parts else "暂无法处理该复合问题",
            "data": {"fused": False, "agent_count": len(agent_results)},
        }

    # ------------------------------------------------------------------
    # 路由分发
    # ------------------------------------------------------------------

    async def route_to_agent(
        self, agent_type: str, message: str, user_id: str | None = None,
        user_profile: dict | None = None,
    ) -> dict[str, Any]:
        """路由到对应智能体处理请求

        根据智能体类型选择不同的处理策略：
        - policy: 优先使用 KnowledgeBase 检索 + LLM 生成
        - health_profile: 优先使用 LLM 生成健康预警（可注入 user_profile 真实数据）
        - 其他: 使用 LLM 对话或降级到 mock 数据

        Args:
            user_profile: 可选的真实用户画像（由 Router 层从数据库查得后注入）。
                          若提供，health/coverage Agent 将基于真实数据分析。
        """
        self._last_user_profile = user_profile

        # 根据智能体类型分发
        if agent_type == "policy":
            return await self._handle_policy_agent(message, user_profile)
        elif agent_type == "health_profile":
            return await self._handle_health_agent(message, user_id, user_profile)
        elif agent_type == "coverage":
            return await self._handle_coverage_agent(message, user_profile)
        elif agent_type == "eeg":
            return await self._handle_eeg_agent(message, user_id, user_profile)
        else:
            # claims / security 等暂时使用 LLM 或 mock
            return await self._handle_generic_agent(agent_type, message, user_profile)

    async def _handle_policy_agent(self, message: str, user_profile: dict | None = None) -> dict[str, Any]:
        """处理政策查询智能体

        使用 KnowledgeBase 检索相关政策，再用 LLM 生成回答。
        若提供 user_profile，结合用户慢病/参保类型做个性化匹配。
        """
        # 0. 个性化查询改写：把用户慢病加入检索 query
        search_query = message
        if user_profile and user_profile.get("found"):
            chronic = user_profile.get("chronic_diseases") or []
            ins_type = user_profile.get("insurance_type", "")
            if chronic:
                search_query = f"{message}（用户情况：{ins_type}，慢病：{'、'.join(chronic)}）"

        # 1. 知识库检索
        search_results: list[SearchResult] = []
        if self._kb is not None:
            try:
                search_results = await self._kb.search(search_query, top_k=5, min_score=0.3)
                logger.info("知识库检索到 %d 条相关结果", len(search_results))
            except Exception as e:
                logger.error("知识库检索失败: %s", e)

        # 2. 如果有检索结果，使用 RAG 生成回答
        if search_results and self._llm is not None:
            try:
                # 构建上下文
                context = [
                    f"来源: {r.source} | 标题: {r.title}\n{r.content}"
                    for r in search_results
                ]

                # 个性化系统提示
                sys_prompt = "你是医保智脑的政策参谋。请基于政策资料准确回答，结合用户实际情况给出可享受的政策建议，并引用来源。"
                if user_profile and user_profile.get("found"):
                    sys_prompt += (
                        f"\n\n## 用户情况：{user_profile.get('name', '')}，"
                        f"{user_profile.get('age', '')}岁，{user_profile.get('insurance_type', '')}，"
                        f"慢病：{'、'.join(user_profile.get('chronic_diseases', []) or ['无'])}。"
                        "请优先匹配该用户能享受的政策。"
                    )

                # 使用 RAG 生成回答
                answer = await self._llm.chat_with_rag(
                    system_prompt=sys_prompt,
                    user_message=message,
                    context=context,
                )

                # 构建来源引用
                sources = list({
                    f"{r.title}（{r.source}）" for r in search_results[:3]
                })

                return {
                    "response": answer,
                    "data": {
                        "matched_count": len(search_results),
                        "sources": sources,
                        "top_policy": search_results[0].title if search_results else "",
                        "scores": [round(r.score, 4) for r in search_results[:3]],
                    },
                    "evidence": [
                        {"type": "policy_source", "title": r.title, "source": r.source, "score": round(r.score, 4)}
                        for r in search_results[:3]
                    ],
                }
            except Exception as e:
                logger.error("RAG 生成失败: %s，降级到检索结果拼接", e)

        # 3. 降级：直接返回检索结果（无 LLM）
        if search_results:
            # 拼接检索结果作为回答
            answer_parts = []
            for i, r in enumerate(search_results[:3], 1):
                answer_parts.append(f"**{i}. {r.title}**（来源: {r.source}）\n{r.content[:300]}")

            return {
                "response": f"为您匹配到 {len(search_results)} 条相关政策：\n\n" + "\n\n".join(answer_parts),
                "data": {
                    "matched_count": len(search_results),
                    "top_policy": search_results[0].title,
                    "sources": [f"{r.title}（{r.source}）" for r in search_results[:3]],
                },
            }

        # 4. 最终降级：mock 数据
        logger.warning("政策查询降级到 mock 数据")
        return self.MOCK_RESPONSES.get("policy", {"response": "暂无法处理该请求", "data": {}})

    async def _handle_health_agent(self, message: str, user_id: str | None = None,
                                   user_profile: dict | None = None) -> dict[str, Any]:
        """处理健康画像智能体

        优先使用数据库真实用户画像，配合 LLM 生成个性化健康预警和建议。
        """
        # 优先用注入的真实画像，否则用兜底假数据
        if user_profile and user_profile.get("found"):
            user_data = {
                "user_id": user_id,
                "name": user_profile.get("name", ""),
                "age": user_profile.get("age", 55),
                "chronic_diseases": user_profile.get("chronic_diseases", []),
                "medications": user_profile.get("medications", []),
                "medication_categories": user_profile.get("medication_categories", []),
                "recent_visits": user_profile.get("recent_visits", 0),
                "visit_count_6m": user_profile.get("visit_count_6m", 0),
                "diagnoses": user_profile.get("diagnoses", []),
                "medication_count": len(user_profile.get("medications", [])),
            }
        else:
            user_data = {
                "user_id": user_id,
                "age": 55,
                "chronic_diseases": ["高血压"],
                "recent_visits": 3,
                "medication_count": 2,
            }

        if self._llm is not None:
            try:
                alert_result = await self._llm.generate_health_alert(user_data)

                # 生成健康建议回答
                risk_level = alert_result.get("risk_level", "low")
                risk_label = {"low": "低风险", "medium": "中风险", "high": "高风险"}.get(risk_level, "未知")

                alerts_text = []
                for alert in alert_result.get("alerts", []):
                    alerts_text.append(
                        f"- **{alert.get('type', '')}**: {alert.get('description', '')}\n"
                        f"  建议: {alert.get('suggestion', '')}\n"
                        f"  政策提示: {alert.get('related_policy', '')}"
                    )

                response = f"您的健康风险评估：**{risk_label}**\n\n"
                if alerts_text:
                    response += "⚠️ 预警信息：\n" + "\n".join(alerts_text)
                else:
                    response += "暂无明显风险，请继续保持健康生活方式。"

                return {
                    "response": response,
                    "data": {
                        "health_score": 70 if risk_level == "low" else (50 if risk_level == "medium" else 30),
                        "risk_level": risk_level,
                        "chronic_diseases": user_data.get("chronic_diseases", []),
                        "alert_count": len(alert_result.get("alerts", [])),
                    },
                }
            except Exception as e:
                logger.error("健康预警生成失败: %s，降级到 mock 数据", e)

        # 降级：mock 数据
        return self.MOCK_RESPONSES.get("health_profile", {"response": "暂无法处理该请求", "data": {}})

    async def _handle_coverage_agent(self, message: str, user_profile: dict | None = None) -> dict[str, Any]:
        """处理报销待遇智能体

        尝试从知识库检索相关报销政策，再用 LLM 生成回答。
        若提供 user_profile，结合参保类型做个性化回答。
        """
        search_query = message
        if user_profile and user_profile.get("found"):
            ins_type = user_profile.get("insurance_type", "")
            emp = user_profile.get("employee_status", "")
            search_query = f"{message}（用户：{ins_type}/{emp}）"

        # 尝试从知识库获取报销相关信息
        if self._kb is not None:
            try:
                search_results = await self._kb.search(search_query, top_k=3, category="职工医保/居民医保基本政策", min_score=0.3)
                if not search_results:
                    search_results = await self._kb.search(search_query, top_k=3, min_score=0.3)

                if search_results and self._llm is not None:
                    context = [
                        f"来源: {r.source} | 标题: {r.title}\n{r.content}"
                        for r in search_results
                    ]
                    sys_prompt = "你是医保智脑的权益管家，请根据政策资料准确回答用户的报销比例、起付线、封顶线、个人账户等问题。"
                    if user_profile and user_profile.get("found"):
                        sys_prompt += (
                            f"\n\n## 用户情况：{user_profile.get('name', '')}，"
                            f"{user_profile.get('insurance_type', '')}，{user_profile.get('employee_status', '')}。"
                            "请给出该用户适用的具体待遇数据。"
                        )
                    answer = await self._llm.chat_with_rag(
                        system_prompt=sys_prompt,
                        user_message=message,
                        context=context,
                    )
                    return {
                        "response": answer,
                        "data": {
                            "matched_count": len(search_results),
                            "sources": [f"{r.title}（{r.source}）" for r in search_results[:3]],
                        },
                        "evidence": [
                            {"type": "policy_source", "title": r.title, "source": r.source}
                            for r in search_results[:3]
                        ],
                    }

                if search_results:
                    return {
                        "response": f"根据政策资料：{search_results[0].content[:300]}",
                        "data": {
                            "matched_count": len(search_results),
                            "top_policy": search_results[0].title,
                        },
                    }
            except Exception as e:
                logger.error("报销查询失败: %s", e)

        # 降级：mock 数据
        return self.MOCK_RESPONSES.get("coverage", {"response": "暂无法处理该请求", "data": {}})

    async def _handle_eeg_agent(
        self, message: str, user_id: str | None = None,
        user_profile: dict | None = None,
    ) -> dict[str, Any]:
        """处理脑电健康智能体（第 6 个智能体「脑电卫士」，BCI×医保核心创新）

        流程：EEG 采集（合成信号）→ 频域特征提取 → 健康指标 → 异常预警 → 医保政策联动
        若有 LLM，进一步用自然语言解读脑电结果；否则用结构化模板回答。
        """
        from app.services.eeg import engine as eeg_engine

        # 根据用户画像推荐心理状态（Demo 时模拟采集场景）
        mental_state = eeg_engine.pick_mental_state_by_profile(user_profile)
        session = eeg_engine.assess_session(
            user_id=user_id or "1",
            mental_state=mental_state,
            duration_seconds=4,
            user_profile=user_profile,
            seed=42,
        )

        metrics = session.metrics
        alerts = session.alerts
        policy_links = session.policy_links

        # 结构化文本回答（无论是否有 LLM 都先构造，LLM 可在此基础上润色）
        name = (user_profile or {}).get("name", "您")
        stress = metrics.get("stress_index", 0)
        attention = metrics.get("attention_index", 0)
        sleep = metrics.get("sleep_quality", 0)
        cognitive = metrics.get("cognitive_load", 0)
        emotion = metrics.get("emotion", {})
        emotion_label = emotion.get("label", "平稳")

        parts = [
            f"**脑电健康评估完成**（{name}，心理状态：{session.mental_state_label}）\n",
            f"- 压力指数：{stress}/100",
            f"- 注意力指数：{attention}/100",
            f"- 睡眠质量：{sleep}/100",
            f"- 认知负荷：{cognitive}/100",
            f"- 情绪状态：{emotion_label}\n",
        ]

        if alerts:
            parts.append(f"⚠️ 检测到 {len(alerts)} 项脑电健康预警：")
            for a in alerts[:3]:
                parts.append(f"- **{a.get('title', '')}**：{a.get('description', '')}")
                if a.get("suggestion"):
                    parts.append(f"  建议：{a.get('suggestion')}")
        else:
            parts.append("✅ 脑电指标正常，未发现异常预警。")

        if policy_links:
            parts.append(f"\n💡 已为您匹配 {len(policy_links)} 项相关医保政策：")
            for p in policy_links[:3]:
                parts.append(f"- **{p.get('policy_hint', '')}**：{p.get('suggestion', '')}")

        structured_response = "\n".join(parts)

        # 若 LLM 可用，用 LLM 润色为更自然的回答
        if self._llm is not None:
            try:
                sys_prompt = (
                    "你是医保智脑的脑电卫士智能体（EEG Agent），负责解读 EEG 脑电评估结果并给出健康建议。"
                    "基于五频段功率（δ/θ/α/β/γ）和四维健康指标（压力/注意力/睡眠/认知负荷）解读用户脑电状态，"
                    "并主动推荐相关医保政策。回答要专业、温暖、可操作，体现'脑电采集→健康评估→医保联动'全链路。"
                )
                if user_profile and user_profile.get("found"):
                    sys_prompt += (
                        f"\n\n## 用户情况：{user_profile.get('name', '')}，"
                        f"{user_profile.get('age', '')}岁，{user_profile.get('insurance_type', '')}，"
                        f"慢病：{'、'.join(user_profile.get('chronic_diseases', []) or ['无'])}。"
                    )
                user_msg = (
                    f"用户问题：{message}\n\n"
                    f"脑电评估结果（结构化数据）：\n{structured_response}\n\n"
                    f"频段功率：{session.avg_band_powers}\n"
                    f"健康指标：{metrics}\n"
                    f"联动政策：{policy_links}"
                )
                answer = await self._llm.chat(
                    messages=[
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.5,
                )
                return {
                    "response": answer,
                    "data": {
                        "mental_state": session.mental_state,
                        "mental_state_label": session.mental_state_label,
                        "metrics": metrics,
                        "alert_count": len(alerts),
                        "policy_link_count": len(policy_links),
                        "session_id": session.session_id,
                    },
                    "evidence": [
                        {"type": "eeg_metric", "metric": k, "value": v}
                        for k, v in metrics.items() if isinstance(v, (int, float))
                    ] + [
                        {"type": "eeg_policy_link", "policy": p.get("policy_hint")}
                        for p in policy_links[:3]
                    ],
                }
            except Exception as e:
                logger.error("EEG Agent LLM 解读失败: %s，降级结构化回答", e)

        # 降级：直接返回结构化回答
        return {
            "response": structured_response,
            "data": {
                "mental_state": session.mental_state,
                "mental_state_label": session.mental_state_label,
                "metrics": metrics,
                "alert_count": len(alerts),
                "policy_link_count": len(policy_links),
                "session_id": session.session_id,
            },
            "evidence": [
                {"type": "eeg_metric", "metric": k, "value": v}
                for k, v in metrics.items() if isinstance(v, (int, float))
            ] + [
                {"type": "eeg_policy_link", "policy": p.get("policy_hint")}
                for p in policy_links[:3]
            ],
        }

    async def _handle_generic_agent(self, agent_type: str, message: str,
                                    user_profile: dict | None = None) -> dict[str, Any]:
        """处理通用智能体（claims / security 等）

        优先使用专业 Agent 提示词 + LLM 对话，不可用时降级到 mock 数据。
        """
        if self._llm is not None:
            try:
                # 优先使用 prompts/agent_prompts.py 里的专业系统提示词
                agent_descriptions = {
                    "claims": "你是医保智脑的报销助手，帮助用户了解报销流程、准备报销材料、解读报销差额。回答要专业、具体、可操作。",
                    "security": "你是医保智脑的安全守门，解答用户关于数据授权、隐私保护、审计追溯、可信数据空间的问题。强调'数据可用不可见'理念。",
                }
                system_prompt = agent_descriptions.get(agent_type, "你是医保智脑的智能助手，请专业、准确地回答用户问题。")

                # 注入用户上下文
                user_msg = message
                if user_profile and user_profile.get("found"):
                    user_msg = (
                        f"[用户上下文：{user_profile.get('name', '')}，{user_profile.get('age', '')}岁，"
                        f"{user_profile.get('insurance_type', '')}，慢病：{'、'.join(user_profile.get('chronic_diseases', []) or ['无'])}]\n\n"
                        f"用户问题：{message}"
                    )

                answer = await self._llm.chat(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    temperature=0.5,
                )
                return {
                    "response": answer,
                    "data": {"agent_type": agent_type},
                }
            except Exception as e:
                logger.error("LLM 对话失败: %s，降级到 mock 数据", e)

        # 降级：mock 数据
        return self.MOCK_RESPONSES.get(agent_type, {"response": "暂无法处理该请求", "data": {}})

    # ------------------------------------------------------------------
    # 结果聚合
    # ------------------------------------------------------------------

    def aggregate_results(self, result: dict[str, Any], agent_type: str = "") -> dict[str, Any]:
        """聚合智能体结果，补充建议"""
        suggestions_map: dict[str, list[str]] = {
            "coverage": [
                "查看您近12个月的缴费明细",
                "测算不同医院的报销差异",
                "了解门诊慢病待遇如何提高报销比例",
            ],
            "claims": [
                "上传发票让我帮您预审报销金额",
                "查看报销所需材料清单",
                "了解报销进度和到账情况",
            ],
            "health_profile": [
                "查看完整的健康画像雷达图",
                "了解近期用药安全提醒",
                "获取个性化健康改善建议",
            ],
            "policy": [
                "查看为您匹配的省钱政策清单",
                "了解门诊慢病认定申请流程",
                "查询异地就医备案操作",
            ],
            "security": [
                "管理智能体数据访问授权",
                "查看完整的审计日志",
                "了解您的数据权利",
            ],
            "eeg": [
                "发起一次脑电采集会话",
                "查看脑电健康趋势",
                "了解脑电异常对应的医保政策",
            ],
        }
        suggestions = suggestions_map.get(agent_type, [
            "您可以问我关于医保报销比例的问题",
            "需要理赔帮助？试试上传发票图片",
            "查看您的健康画像和风险预警",
        ])
        agent_type_label = {
            "coverage": "coverage_agent",
            "claims": "claims_agent",
            "health_profile": "health_agent",
            "policy": "policy_agent",
            "security": "security_agent",
            "eeg": "eeg_agent",
        }.get(agent_type, "orchestrator_agent")
        return {
            "agent_type": agent_type_label,
            "response": result.get("response", ""),
            "data": result.get("data", {}),
            "evidence": result.get("evidence"),
            "suggestions": suggestions,
        }
