# MedSignal · 多模态医疗信号智能体

> 面向真实医疗场景的关键医疗信号识别智能体 —— 脑电信号 × 医学影像 × 生理行为信号
> 参赛：VentureD Hackathon 医疗赛道（AI 智能体 · 关键医疗信号识别）

MedSignal 围绕医疗赛道"**关键医疗信号识别**"方向，从三类真实医疗信号入手，帮助医生与患者不遗漏任何关键信号：**脑电信号**（EEG 频域分析 → 压力/睡眠/注意力/情绪五维健康指标）、**医学影像信号**（CT/胸片/MRI 病灶检测 → AI 预标注 → 医师复核 → 结构化报告）、**生理行为信号**（用药/就医/购药模式 → 慢病风险主动预警）；同时以"患者信息连接"能力把专业医疗与政策信息翻译成患者可理解、可行动的建议。

## 一分钟看懂

MedSignal 是一个可本地运行的医疗健康智能体工作台。普通用户可以在同一界面里聊天、切换或添加用户、查看健康画像和医保信息，并通过 3D 数字人体整理就诊档案；开发者可以继续接入真实大模型、医院数据、脑电设备和影像模型。

当前仓库包含两种运行方式：

- **离线演示模式（默认）**：不需要任何 API Key。聊天通过意图识别、规则引擎和安全的演示数据回答，所有主要页面都能使用。
- **大模型模式**：将 `DEMO_OFFLINE=false` 并配置 OpenAI 兼容接口后，可获得更自然的开放式对话、RAG 政策问答和多智能体结果融合。

> 本项目用于技术演示、资料整理和辅助决策，不构成临床诊断或治疗建议。演示数据不应替代真实医疗数据。

### 普通用户可以做什么

1. 在首页和 MedSignal 助手连续对话。
2. 从左侧进入医保权益、健康画像、数字人体档案、脑电、影像、报销和政策功能。
3. 在右上角切换用户，或点击“添加新用户”；新用户会立即联动聊天与数字人体档案。
4. 在数字人体档案中旋转人体模型，按器官和时间查看已有记录。

### 开发者从哪里开始

- 后端 API：`http://localhost:8000/docs`
- 前端入口：`http://localhost:3000`
- 大模型配置：`backend/.env.example`
- 接口契约：`docs/api_contract.md`
- 后续路线图：[NEXT_STEPS.md](NEXT_STEPS.md)

## 📚 文档导航

| 文档 | 说明 | 适合人群 |
|---|---|---|
| [安装部署指南](docs/安装部署指南.md) | 本地开发 / Docker / 云端三种部署方式 + 环境变量 + 问题排查 | 开发者 / 运维 |
| [用户使用手册](docs/用户使用手册.md) | 各功能操作指南 + 脑电评估 + 影像标注 + 常见问题 | 终端用户 |
| [升级完成报告](docs/升级完成报告.md) | 完整升级记录 + EEG/影像集成成果 + 验收结果 | 评委 / 评审 |
| [API 接口文档](docs/api_contract.md) | 全部 API 接口契约 | 开发者 |
| [路演脚本](docs/roadshow_script.md) | 8 分钟路演流程与话术 | 演讲者 |

## ✨ 核心能力

1 个编排智能体 + 8 个专业智能体，覆盖"信号识别 → 信息连接 → 安全合规"完整链路：

**关键医疗信号识别（赛道方向）**
- 🧠 **脑电卫士** — EEG 脑电信号频域分析，输出压力/注意力/睡眠/认知负荷/情绪五维指标，脑电异常 → 健康预警 → 政策联动 ⭐
- 🩻 **影像卫士** — 医学影像病灶检测，AI 预标注 bbox → 医师逐框复核 → 结构化报告 + 政策联动 ⭐
- ❤️ **健康卫士** — 用药/就医/购药行为信号分析，5 维健康评分 + 用药相互作用检测 + 主动预警
- 📇 **档案管家** — 人体健康档案：把用户自述 / 上传的 CT·MRI 报告按器官归档（只增不删、带时间与来源），可检索、按时间并列对比、追问缺失信息、交接政策参谋；**只整理用户提供的信息，不做任何诊断或推断**。内置 10 人完整合成档案、3D 病史、检验、EEG、数据库原始附件预览/上传、AI 来源追溯统表，以及单人/全体 CSV、JSON、ZIP 联调导出（前端 `/body-archive`，总览 `/digital-body/cohort.html`，API `/api/body/*` + `/api/body-archive/*`）。

**患者信息理解与连接（赛道方向）**
- 🛡️ **权益管家** — 医疗权益查询、报销测算（多场景对比）
- 📋 **报销助手** — OCR 票据识别 + 7 步分步推导报销计算 + 大病保险
- 📖 **政策参谋** — 用户画像精准匹配政策 + 省钱清单计算

**医疗安全与合规**
- 🔒 **安全守门** — 数据授权管理 + 可信数据空间 + 区块链存证，明确产品使用边界

## 🏆 创新亮点

- **多模态信号识别**：脑电（EEG 频域分析）+ 影像（病灶检测）+ 行为（用药模式）三类关键医疗信号统一由编排智能体调度
- **医师在环（Human-in-the-Loop）**：影像 AI 预标注只是建议，必须由医师逐框确认/驳回后生成最终报告，守住医疗安全底线
- **脑电健康第 6 维**：4 通道/256Hz/五频段（δθαβγ）→ 压力/注意力/睡眠/认知负荷/情绪五维指标
- **多智能体协作**：复合意图并行调度（如"脑电异常+政策省钱"→ eeg+policy 并行）
- **主动式健康预警**：登录即推送，健康预警 + 脑电预警合并展示
- **可信数据空间可视化**：隐私计算"可用不可见" + 区块链存证模拟
- **全链路可解释性**：每个 AI 决策可展开证据链（含脑电指标 evidence、影像 bbox、政策原文引用）
- **动态用户管理**：内置 10 个画像一键切换，也可现场新增用户并立即联动聊天、健康功能和数字人体档案
- **连续对话**：通用问答与 7 类专业意图自动路由，会话及消息记录持久化保存
- **3D 解剖档案联动**：复用用户与就诊数据库，男/女两套解剖模型，支持器官标记、档案聚焦、时间轴回放和追加写入 API

## 🚀 快速开始

### 后端
```bash
cd backend
python -m venv venv && venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 配置 API Key（可选，不配也能跑，会自动降级到规则引擎）
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY 等
# 若要启用大模型，还需设置 DEMO_OFFLINE=false

# 初始化数据库 + 构建知识库（首次）
python scripts/init_db.py
python scripts/build_knowledge_base.py

# 启动
uvicorn app.main:app --reload --port 8000
# 访问 http://localhost:8000/docs 查看 API
```

### 前端
```bash
cd frontend
pnpm install
pnpm dev
# 访问 http://localhost:3000
```

### 验证
```bash
cd backend
python -m pytest tests/                    # 单元测试
python -m scripts.smoke_test               # 端到端冒烟测试
```

## 🧪 测试

| 测试套件 | 说明 |
|---|---|
| 单元测试 | 四大算法引擎（报销/健康/政策/脑电）+ 影像引擎 + 设备适配层 |
| 端到端冒烟 | 全部 Router + AI 对话 + EEG 脑电 + 影像分析 + 多用户 |

```bash
python -m pytest tests/ -v
```

## 📊 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Next.js 14 + React 18 + TypeScript + TailwindCSS + shadcn/ui + ECharts + Framer Motion |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| AI/LLM | OpenAI 兼容 API（aiping 网关 Kimi-K3 主力 + 阿里 DashScope 备选 + GLM-4.6V 视觉模型） |
| 向量库 | ChromaDB + sentence-transformers（离线嵌入，无网络依赖） |
| 脑电分析 | numpy（FFT/Welch PSD 频域分析 + 合成 EEG 信号生成） |
| 医学影像 | 确定性病灶生成 + SVG 影像渲染 + bbox 叠加 + 医生复核工作流 |
| OCR | OCR.space |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 部署 | Docker Compose / Vercel + Render / nginx |

## 📁 项目结构

```
medsignal/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── crud.py              # 统一数据访问层
│   │   ├── auth.py              # 鉴权层
│   │   ├── models.py / schemas.py
│   │   ├── routers/             # 全部 Router（含 eeg、imaging、body / body_archive、users）
│   │   ├── services/
│   │   │   ├── orchestrator.py  # 编排器（多意图 + 融合 + 信号调度）
│   │   │   ├── claims_engine.py # 报销计算引擎
│   │   │   ├── health_engine.py # 健康风险评分引擎
│   │   │   ├── policy_matcher.py# 政策匹配引擎
│   │   │   ├── eeg/engine.py    # 脑电健康引擎（EEG 频域分析）⭐⭐
│   │   │   ├── imaging/         # 医学影像引擎（病灶生成/标注/报告/政策联动）⭐⭐
│   │   │   ├── llm_service.py / knowledge_base.py / ocr_service.py
│   │   └── prompts/agent_prompts.py  # 各 Agent 提示词
│   ├── data/                    # 仿真数据 + 政策库 + 规则库 + 脑电/影像政策联动
│   ├── tests/                   # 单元测试（含 EEG 引擎、影像引擎）
│   └── scripts/                 # 数据生成/初始化/冒烟测试
├── frontend/
│   └── src/
│       ├── app/                 # 页面（首页/脑电健康/影像标注/数字人体档案/权益/报销/政策/安全）
│       ├── components/          # UserSwitcher / EvidencePanel / ProactiveAlertBanner
│       └── lib/                 # api.ts / mock-data.ts / user-context.tsx
├── docs/                        # 安装部署/使用手册/PPT大纲/路演稿/申报书
├── docker-compose.yml / nginx.conf / render.yaml
└── .github/workflows/ci.yml     # CI/CD（lint + test + build）
```

## 📖 文档

- [PPT 大纲](docs/ppt_outline.md) — 16 页路演 PPT
- [路演逐字稿](docs/roadshow_script.md) — 8 分钟脚本 + Q&A
- [项目申报书](docs/项目申报书.md) — 参赛申报材料
- [API 契约](docs/api_contract.md) — 前后端接口真理源
- [安装部署指南](docs/安装部署指南.md) / [用户使用手册](docs/用户使用手册.md)

## 🔐 环境变量

见 `.env.example`。关键项：
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL` — 主力 LLM（aiping 网关 Kimi-K3）
- `VISION_API_KEY` / `VISION_BASE_URL` / `VISION_MODEL` — 视觉模型（aiping 网关 GLM-4.6V，医学影像解读，可选）
- `DASHSCOPE_API_KEY` / `DASHSCOPE_MODEL` — 备选 LLM（阿里）
- `OCR_API_KEY` — OCR.space
- `YIBAO_API_KEY` — API 鉴权（可选，不配则开放）

> 💡 不配置任何 API Key 也能运行：所有功能会自动降级到规则引擎 + mock 数据，保证 Demo 不翻车。

### 大模型调用说明

项目使用 OpenAI 兼容协议，代码入口位于 `backend/app/services/llm_service.py`：

- 主调用：`LLM_BASE_URL` + `LLM_API_KEY` + `LLM_MODEL`，示例默认是 aiping 网关的 `Kimi-K3`。
- 备用调用：`DASHSCOPE_BASE_URL` + `DASHSCOPE_API_KEY` + `DASHSCOPE_MODEL`，示例默认是阿里云 DashScope 的 `qwen-plus`。
- 视觉解读：`VISION_BASE_URL` + `VISION_API_KEY` + `VISION_MODEL`，为可选能力。
- 当 `DEMO_OFFLINE=true` 时，后端会主动跳过 LLM 和知识库初始化，因此即使填了 Key 也不会调用大模型。

## 🛡️ 容错降级

三级降级保证 Demo 绝不翻车：
1. **LLM**：Kimi-K3 → DashScope → 关键词匹配 + 规则引擎
2. **知识库**：API Embedding → ChromaDB 默认嵌入 → mock
3. **前端**：后端 API → 本地 mock-data.ts

## 🐳 Docker 部署

```bash
docker-compose up -d
# 前端 :3000 / 后端 :8000 / postgres :5432 / redis :6379 / chromadb :8001
```

---

**让关键医疗信号，不再被错过。** 🏆
