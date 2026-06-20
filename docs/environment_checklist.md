# 开发环境与云服务API准备检查清单

> 在7月3日黑客松前，确保以下所有项目已完成

---

## 1. 开发环境

### 基础工具
- [ ] Node.js 18+ 已安装（`node -v` 验证）
- [ ] pnpm 已安装（`pnpm -v` 验证）
- [ ] Python 3.11+ 已安装（`python --version` 验证）
- [ ] Git 已安装并配置 SSH Key（`git --version` 验证）
- [ ] VS Code 已安装，插件：Python、Tailwind CSS IntelliSense、Docker、GitLens、ESLint

### Docker 环境
- [ ] Docker Desktop 已安装并运行（`docker --version` 验证）
- [ ] Docker Compose 可用（`docker-compose --version` 验证）
- [ ] 运行 `docker-compose up` 验证所有服务可启动

### 数据库
- [ ] PostgreSQL 可通过 Docker 访问（localhost:5432）
- [ ] Redis 可通过 Docker 访问（localhost:6379）
- [ ] ChromaDB 可通过 Docker 访问（localhost:8001）

---

## 2. 云服务与 API Key

### LLM API（核心，必须有）
- [ ] DeepSeek API Key 已获取并充值（主力模型）
  - 注册地址：https://platform.deepseek.com
  - 余额 ≥ ¥50
  - 测试：`curl https://api.deepseek.com/chat/completions` 可用
- [ ] 通义千问 API Key 已获取（备选模型）
  - 注册地址：https://dashscope.console.aliyun.com
  - 测试可用

### OCR API（报销预审功能）
- [ ] 百度云 OCR API Key + Secret Key 已获取
  - 注册地址：https://cloud.baidu.com/doc/OCR/s/Ek3h7yeiq
  - 通用文字识别（标准版）已开通
  - 测试：可识别一张票据图片
- [ ] PaddleOCR 本地模型已下载（离线备选）
  - `pip install paddleocr paddlepaddle` 成功
  - 测试：可识别一张中文图片

### 向量数据库
- [ ] ChromaDB 本地实例可用（Docker 或 pip 安装）
- [ ] 测试：可插入和查询向量数据

---

## 3. 项目验证

### 前端
- [ ] `cd frontend && pnpm install` 成功
- [ ] `pnpm dev` 可启动，访问 http://localhost:3000 正常
- [ ] `pnpm build` 构建成功

### 后端
- [ ] `cd backend && pip install -r requirements.txt` 成功
- [ ] `uvicorn app.main:app --reload` 可启动，访问 http://localhost:8000/docs 正常
- [ ] 健康检查端点 `GET /api/health` 返回 200

### 数据
- [ ] `python scripts/generate_data.py` 可生成仿真数据
- [ ] `python scripts/init_db.py` 可初始化数据库
- [ ] `data/mock_data.json` 文件存在且包含 10 个用户数据
- [ ] `data/policy_knowledge.json` 文件存在且包含 18 篇政策文档
- [ ] `data/receipts/` 目录下有 3 张发票图片

### 知识库
- [ ] `python scripts/build_knowledge_base.py` 可构建向量索引
- [ ] 10 个测试查询均有返回结果

---

## 4. 路演准备

### 硬件
- [ ] 笔记本电脑充满电 + 带充电器
- [ ] 手机热点备用（防现场WiFi不稳定）
- [ ] U盘备份项目代码和Demo视频

### 文档
- [ ] 路演逐字稿已打印/在手机上可查看
- [ ] PPT已制作完成（16页）
- [ ] Demo备份视频已录制

### 排练
- [ ] 路演排练至少 2 遍，计时在 8 分钟内
- [ ] Demo流程排练至少 3 遍，无卡顿
- [ ] Q&A准备答案已熟悉

---

## 5. 关键日期提醒

| 日期 | 事项 |
|------|------|
| 6月20日 17:00 | 报名截止 ✅ 已完成 |
| 6月22日 19:00 | 赛道及规则解读（线上） |
| 6月25日 19:00 | 线上答疑 |
| 7月2日晚 | 所有预准备完成 |
| 7月3日 15:00 | 签到入场 |
