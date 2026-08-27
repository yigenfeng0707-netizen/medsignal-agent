# 医保智脑 · 前后端 API 契约（真理源）

> 版本：v2.0（P0 升级后）
> 约定：本文件是所有 API 端点的请求/响应契约真理源。前后端任一方变更需同步更新本文档。

## 通用约定
- Base URL：`http://localhost:8000`（开发）/ `https://yibao-zhinao-api.onrender.com`（生产）
- 所有数据端点返回 JSON
- `user_id` 接受三种格式：`1` / `"001"` / `"user_001"`，后端 `_normalize_user_id` 统一为 int
- 时间格式：ISO 8601（`2026-06-15T08:30:00`）

---

## 1. 智能体对话

### POST `/api/agents/chat`
**请求**：`ChatRequest`
```json
{ "message": "我的医保能报多少", "user_id": "user_001", "conversation_id": "可选" }
```
**响应**：
```json
{
  "agent_type": "coverage_agent",
  "response": "（LLM/RAG 生成的自然语言回答）",
  "data": { "matched_count": 3, "sources": [...] },
  "evidence": [{ "type": "policy_source", "title": "...", "source": "..." }],
  "suggestions": ["查看您近12个月的缴费明细", ...],
  "user_profile": { "name": "张阿姨", "age": 58, "insurance_type": "职工医保", "chronic_diseases": ["糖尿病"] },
  "conversation_id": "..."
}
```

---

## 2. 医保待遇

### GET `/api/coverage/{user_id}`
**响应**：
```json
{
  "user": { "id": "user_001", "name": "张阿姨", "age": 58, "gender": "女", "city": "杭州", "insurance_type": "职工医保", "employee_status": "退休" },
  "payment_years": "15年3个月",
  "payment_months": 183,
  "account_balance": 3425.20,
  "outpatient_ratio": 0.90,
  "inpatient_ratio": 0.95,
  "payment_history": [{ "year": 2025, "month": 1, "personal_amount": 385.50, "company_amount": 771.00, "base_amount": 6425 }],
  "payment_history_values": [385.50, 385.50, ...],
  "recent_activities": [{ "date": "2025-06-15", "type": "缴费", "desc": "6月医保缴费到账", "amount": "+¥398.00" }]
}
```
> 前端 `getCoverageSummary` 会把 `payment_history`（对象数组）转换为 number[]（取 personal_amount），或直接用 `payment_history_values`。

### GET `/api/coverage/{user_id}/estimate`
**查询参数**：`total_cost`, `visit_type=住院`, `hospital_level=二级`, `chronic_disease=false`, `cross_region=false`
**响应**：含 `comparison`（社区/二级/三级三档对比）+ `explanation`

---

## 3. 理赔助手

### POST `/api/claims/ocr`
**请求**：`multipart/form-data`，字段 `file`
**响应**：`{ ocr_result: {...}, confidence: 0.95 }`

### POST `/api/claims/pre-review`
**请求**：`{ "total_amount": 253.50, "visit_type": "门诊", "insurance_type": "职工医保" }`
**响应**：
```json
{
  "total_amount": 253.50, "deductible": 800, "class_b_deduction": 0,
  "reimbursable_amount": 253.50, "reimbursement_ratio": 0.75,
  "estimated_reimbursement": 0, "out_of_pocket": 253.50, "cap": 5000,
  "steps": [{ "name": "费用分类", "detail": "...", "amount": 253.50 }, ...],
  "explanation": "（自然语言总结）",
  "required_documents": [{ "name": "门诊病历", "status": "uploaded" }, ...]
}
```

---

## 4. 健康画像

### GET `/api/health/{user_id}/profile`
**响应**：
```json
{
  "health_score": 72, "score_label": "良好",
  "radar_data": [{ "name": "慢病管理", "value": 58, "score": 58, "target": 80 }, ...],
  "alerts": [{ "level": "high", "severity": "high", "icon": "🔴", "title": "...", "desc": "...", "description": "...", "suggestion": "...", "action": "...", "evidence": [...] }],
  "medications": [{ "name": "...", "dosage": "...", "frequency": "...", "status": "正常", "statusColor": "text-green-600 bg-green-50", "category": "..." }],
  "trend_data": [{ "month": "2025-06", "score": 72 }],
  "suggestions": [{ "title": "...", "description": "...", "priority": "high", "icon": "📊", "color": "red" }]
}
```
> `radar_data` 同时提供 `name`/`value`（前端雷达图用）和 `score`（兼容）。`alerts` 同时提供 `severity`（前端用）和 `level`（后端语义），以及 `desc`/`description`、`action`/`suggestion` 双字段。

### GET `/api/health/{user_id}/alerts` → `alerts: [...]`
### GET `/api/health/{user_id}/trends` → `{ trends: {...}, health_trend: [...] }`

---

## 5. 政策解读

### GET `/api/policy/match/{user_id}`
**响应**：
```json
{
  "user_id": "user_001", "total_savings": 7600, "matched_count": 4,
  "policies": [{ "id": "policy_001", "title": "...", "match_score": 0.95, "annual_savings": 3600, "match_reason": "...", "matchReason": "...", "category": "...", "deadline": "2026-03-31", "steps": [...] }],
  "evidence": { "chronic_diseases": [...], "insurance_type": "...", "annual_medical_cost": 12345 }
}
```

### POST `/api/policy/search`
**请求**：`{ "query": "门诊慢病", "category": null }`
**响应**：`{ keyword, results: [...], total }`

### GET `/api/policy/{policy_id}` → 政策文档详情

---

## 6. 数据安全

### GET `/api/security/authorizations/{user_id}`
**响应**：`active_authorizations`, `anomalies`, `today_accesses`, `authorization_matrix`, `rights`, `active_auths`, `audit_log`（含 `proof_hash`）

### POST `/api/security/authorize`
**请求**：`AuthorizationRequest`（user_id, data_type, authorized_agent, duration_days）
**响应**：含 `proof_hash`（存证哈希）

### GET `/api/security/audit-log/{user_id}` → `logs: [...]`
### GET `/api/security/data-flow/{user_id}` → 可信数据空间流转记录（P2-2 可视化用）

---

## 6.5 EEG 脑电健康（BCI×医保创新，赛道7核心）

### GET `/api/eeg/states` → `{ states: [...] }`

### POST `/api/eeg/{user_id}/session`
**查询参数**：`mental_state=relaxed&duration_seconds=4`
**响应**：`EEGSession`
```json
{
  "session_id": "eeg_user_001_...",
  "user_id": "user_001",
  "metrics": {
    "stress_index": 30.5,
    "attention_index": 65.2,
    "sleep_quality": 72.0,
    "cognitive_load": 45.3,
    "emotion": { "valence": 55, "arousal": 40, "label": "平静放松" },
    "ratios": { "alpha_beta": 1.5, "theta_beta": 0.8, "theta_alpha": 0.6, "delta_ratio": 0.2 },
    "cerebrovascular_risk": 25.0,
    "cognitive_decline_risk": 18.5,
    "mental_health": {
      "anxiety_score": 20.0, "depression_score": 15.0,
      "overall_risk": 20.0, "screening_label": "正常"
    }
  },
  "alerts": [{ "level": "high", "category": "cerebrovascular", "title": "...", "evidence": [...] }],
  "policy_links": [{ "trigger": "cerebrovascular_risk", "related_policies": [...] }],
  "waveform": [{ "channel": "TP9", "data": [...] }]
}
```
> ⭐ 赛道7核心新增字段：`cerebrovascular_risk`（脑血管风险指数）、`cognitive_decline_risk`（认知衰退风险）、`mental_health`（精神状态筛查）。预警 `category` 新增 `cerebrovascular`/`cognitive_decline`/`mental_health`。

### GET `/api/eeg/{user_id}/latest` → `EEGSession`
### GET `/api/eeg/{user_id}/history` → `{ total_sessions, history: [...], trend: [...] }`
### GET `/api/eeg/{user_id}/realtime` → `{ channel, waveform, band_powers, metrics_snapshot }`
### GET `/api/eeg/{user_id}/policy-links` → `{ policy_links: [...] }`

---

## 7. 健康检查

### GET `/api/health` → `{ "status": "ok", "service": "医保智脑" }`

---

## 字段兼容性原则
1. 后端尽量同时提供同义字段（如 `desc`/`description`、`match_reason`/`matchReason`），降低前端适配成本
2. 后端新增字段不破坏前端现有渲染（前端忽略未知字段）
3. 前端在 `lib/api.ts` 对后端返回做必要转换（如 payment_history 对象数组→number[]）
