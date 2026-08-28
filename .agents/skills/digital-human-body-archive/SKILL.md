---
name: digital-human-body-archive
description: 在 MedSignal 项目中把用户的病例、体检和检查资料按解剖部位追加归档，并通过项目内置的交互式 3D 人体查看器展示。用于数字人体、3D 人体档案、器官时间线、部位病史或病例资料接入；不用于诊断、治疗建议或医学影像判读。
---

# MedSignal 数字人体档案

使用项目现有用户、数据库、API 与前端页面维护按部位组织的医疗档案。应用数据库是唯一数据源；不要在技能目录或静态资源目录创建患者 JSON。

## 工作流

1. 明确目标用户，使用项目的 `user_001` 形式 id。没有明确用户时先从当前 MedSignal 用户上下文获取，不得猜测或跨用户混录。
2. 接入记录前阅读 [references/taxonomy.md](references/taxonomy.md)，从用户原文选择器官 key。没有明确侧别时使用通用 key，不猜左/右。
3. 保留用户原文：`description` 只做忠实摘录或轻量整理，`raw_excerpt` 保存原始片段。日期缺失就留空。
4. 通过 `POST /api/body-archive/patients/<user_id>/records` 追加，或运行 `scripts/ingest.py`。不要修改或删除已有记录。
5. 在前端 `/body-archive` 验证患者切换、3D 标记、时间轴和右侧记录面板。

## 项目位置

- 档案管家路由（对话/上传）：`backend/app/routers/body.py`（`/api/body/*`）
- 3D 查看器适配路由：`backend/app/routers/body_archive.py`（`/api/body-archive/*`）
- 分类与抽取：`backend/app/services/body/`（taxonomy.py 器官契约 + extractor.py 信息抽取）
- 数据模型：`backend/app/models.py` 中的 `BodyRecord` / `BodyDocument`（只增不删）
- 3D 查看器：`backend/app/static/digital-body/index.html`（main.py 挂载于 `/digital-body`）
- GLB 模型：`backend/app/static/digital-body/models/`
- 前端入口：`frontend/src/app/body-archive/page.tsx`（iframe 嵌入查看器）
- 模型来源和许可：[references/models.md](references/models.md)

## 接入 API

```bash
python .agents/skills/digital-human-body-archive/scripts/ingest.py \
  --patient user_001 \
  --text "2026年2月查出肺部小结节" \
  --source "对话输入"
```

默认 API 为 `http://127.0.0.1:8000`，可用 `--api` 或 `MEDSIGNAL_API_URL` 修改。生产环境启用 `YIBAO_API_KEY` 时同时传 `--api-key`。

资料接口仅登记文件名与备注，不保存原始文件：

```bash
python .agents/skills/digital-human-body-archive/scripts/ingest.py \
  --patient user_001 --material "胸部CT.pdf" --material-note "复查资料"
```

## 必须保持的边界

- 只整理、不诊断；不得把归档结果表述为病情判断。
- 只追加，不提供更新或删除入口。
- 不猜日期、器官或左右侧。
- 患者数据属于敏感医疗信息；不得提交真实患者资料、数据库文件或上传原件到 Git。
- 查看器固定显示非诊断免责声明，不得移除。
- 3D 模型是解剖位置参考，不是临床测量或诊断工具。

## 验证

```bash
cd backend
python -m pytest tests/test_body_agent.py tests/test_body_archive.py -q
python -m ruff check app/routers/body.py app/routers/body_archive.py app/services/body tests/test_body_archive.py

cd ../frontend
pnpm build
```
