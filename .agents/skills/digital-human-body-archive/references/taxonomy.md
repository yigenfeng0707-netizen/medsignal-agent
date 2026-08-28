# 数字人体器官 key 契约

API、接入脚本和 3D 查看器必须使用同一组 key。代码真理源是 `backend/app/services/body_archive.py` 的 `ORGAN_LABELS`。

| key | 中文标签 | 常见文本 |
|---|---|---|
| `brain` | 脑部 | 脑、颅内、头部 |
| `neck` | 颈部 | 颈部、甲状腺、咽喉 |
| `lungs` | 肺部 | 肺、支气管、呼吸道 |
| `heart` | 心脏 | 心脏、冠心病、心肌、高血压 |
| `liver` | 肝脏 | 肝、肝脏 |
| `stomach` | 胃部 | 胃、胃部 |
| `kidneys` | 肾脏 | 肾、尿路、泌尿 |
| `intestines` | 肠道 | 肠、结肠、直肠、阑尾 |
| `spleen` | 脾脏 | 脾、脾脏 |
| `pancreas` | 胰腺 | 胰、胰腺、糖尿病 |
| `spine` | 脊柱 | 脊柱、颈椎、腰椎、椎间盘 |
| `chest` | 胸部 | 胸部、乳腺、乳房 |
| `abdomen` | 腹部 | 腹部、腹痛 |
| `pelvis` | 盆腔 | 骨盆、盆腔、髋 |
| `uterus` | 子宫 | 子宫、宫腔 |
| `ovaries` | 卵巢 | 卵巢、输卵管 |
| `prostate` | 前列腺 | 前列腺 |
| `shoulder_l` / `shoulder_r` / `shoulder` | 左肩 / 右肩 / 肩部 | 肩、肩膀 |
| `arm_l` / `arm_r` / `arm` | 左臂 / 右臂 / 手臂 | 上肢、肘、腕 |
| `knee_l` / `knee_r` / `knee` | 左膝 / 右膝 / 膝盖 | 膝、膝关节 |
| `leg_l` / `leg_r` / `leg` | 左腿 / 右腿 / 腿部 | 下肢、小腿、踝 |

侧别规则：原文明确出现“左”或“右”才使用 `_l` / `_r`；否则使用通用 key。

## 追加记录请求

`POST /api/body-archive/patients/<user_id>/records`

```json
{
  "organ": "lungs",
  "event_date": "2026-02",
  "source_type": "chat",
  "source_label": "对话输入",
  "source_ref": "",
  "description": "查出肺部小结节",
  "raw_excerpt": "我2026年2月查出肺部小结节"
}
```

`event_date` 仅接受 `YYYY-MM`、`YYYY-MM-DD` 或空字符串。患者 id 接受正整数或 `user_001` 形式。
