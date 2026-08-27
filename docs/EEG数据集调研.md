# EEG 公开数据集调研与真实数据接入方案

> MedSignal 项目 — 真实 EEG 数据接入专项调研
> 调研日期：2026-08-27
> 调研范围：4 个公开 EEG 数据集（PhysioNet eegmmidb + OpenNeuro ds008108 / ds008496 / ds007955）
> 关联文档：[`EEG设备接入指南.md`](./EEG设备接入指南.md)（v2.2 真实设备接入方案）

---

## 目录

- [一、调研结论速览](#一调研结论速览)
- [二、数据集详细元信息](#二数据集详细元信息)
  - [2.1 PhysioNet eegmmidb — 运动执行/想象数据集](#21-physionet-eegmmidb--运动执行想象数据集)
  - [2.2 OpenNeuro ds008108 — OSA 认知障碍多模态数据集](#22-openneuro-ds008108--osa-认知障碍多模态数据集)
  - [2.3 OpenNeuro ds008496 — Gen-AI 学生学习过程数据集](#23-openneuro-ds008496--gen-ai-学生学习过程数据集)
  - [2.4 OpenNeuro ds007955 — 情绪词联想数据集](#24-openneuro-ds007955--情绪词联想数据集)
- [三、与 MedSignal 五维指标的适配性分析](#三与-medsignal-五维指标的适配性分析)
- [四、接入优先级推荐](#四接入优先级推荐)
- [五、本地 EEG 引擎现状（代码勘察）](#五本地-eeg-引擎现状代码勘察)
- [六、接入技术方案建议](#六接入技术方案建议)
- [七、许可证与引用合规](#七许可证与引用合规)
- [附录：下载命令汇总](#附录下载命令汇总)

---

## 一、调研结论速览

四个数据集核心指标对比（✅ = 具备，❌ = 不具备）：

| 维度 | eegmmidb | ds008108 | ds008496 | ds007955 |
|---|---|---|---|---|
| **受试者数** | 109 | 142（OSA 患者+健康对照） | 15（20-22 岁学生） | 9 |
| **EEG 通道数** | 64（10-10 系统） | 6 EEG 导联（PSG 12 通道） | 14（Emotiv EPOC X） | 8（OpenBCI Cyton） |
| **前额通道** | ✅ Fp1/Fp2/AF3/AF4/AF7/AF8 | ❌ 仅 F3/F4/C3/C4/O1/O2（乳突参考） | ✅ AF3/AF4（另有 F3/F4/F7/F8） | ✅ Fp1/Fp2（另有 F3/F4） |
| **采样率** | 160 Hz | 256 Hz | 256 Hz | 250 Hz |
| **单次时长** | 1-2 分钟/run × 14 run | 整夜 PSG + 4 次认知评估 | ~39 分钟/任务 × 2 任务 | ~3 分钟 |
| **数据格式** | EDF+ | EDF（BIDS） | EEGLAB .set + .fdt | EEGLAB .set |
| **任务范式** | 运动执行/想象 + 睁闭眼基线 | 睡眠（PSG）+ 认知任务（SART/PVT 等） | AI 辅助写作（认知负荷） | 情绪词汇联想（恐惧诱发） |
| **标注情况** | T0/T1/T2 事件编码 | 睡眠 events + 行为数据 + 问卷 | events.tsv + 信号质量通道 | events.tsv（词/相似度/新旧） + EDA |
| **许可证** | ODC-By 1.0 | CC0 | CC0 | CC0 |
| **允许 AI 训练** | ✅（需署名） | ✅（无限制） | ✅（无限制） | ✅（无限制） |
| **下载方式** | 直链/wget/S3，无需注册 | OpenNeuro 匿名下载 | OpenNeuro 匿名下载 | OpenNeuro 匿名下载 |
| **推荐优先级** | P2 | **P0** | **P0** | P1 |

**核心结论：**

1. **ds008496 + ds008108 并列 P0**：前者（256Hz + AF3/AF4 前额 + 认知负荷任务）与现有引擎参数完全同构，是"注意力/认知负荷/压力"指标的首选验证源；后者（142 人整夜 PSG + 睡眠分期）是"睡眠质量"指标唯一且高质量的真实验证源，且 EDF 格式直接兼容现有 `load_from_edf`。
2. **ds007955 为 P1**：唯一带明确情绪诱发范式（恐惧词汇）+ 皮肤电（EDA）联动的数据集，含 Fp1/Fp2 前额通道，适配"情绪/精神状态筛查"指标；但样本量小（9 人），仅作概念验证。
3. **eegmmidb 为 P2**：下载最便利（直链免注册）、样本最大（109 人），但 160Hz、运动想象范式与五维指标相关性弱；其**睁眼/闭眼静息基线**是引擎正确性的理想 sanity check（闭眼 α 波增强是经典神经生理现象）。
4. **格式适配工作量**：ds008108 的 EDF 走现有管线零改动；ds008496/ds007955 的 EEGLAB `.set` 格式需新增读取依赖（MNE-Python）或先转换为 EDF/CSV。

---

## 二、数据集详细元信息

### 2.1 PhysioNet eegmmidb — 运动执行/想象数据集

**全名**：EEG Motor Movement/Imagery Dataset（BCI2000 采集）
**主页**：<https://physionet.org/content/eegmmidb/1.0.0/>
**DOI**：[10.13026/C28G6P](https://doi.org/10.13026/C28G6P) ｜ 发布：2009-09-09 ｜ 贡献：Gerwin Schalk et al.（Wadsworth Center, BCI R&D Program）

| 元信息项 | 内容 |
|---|---|
| 受试者数 | 109 名（S001–S109） |
| 通道数 | 64 通道 EEG，国际 10-10 系统（BCI2000 标准布局；**排除** Nz/F9/F10/FT9/FT10/A1/A2/TP9/TP10/P9/P10） |
| 前额通道 | ✅ Fp1、Fp2、AF3、AF4、AF7、AF8 均在列 |
| 采样率 | 160 Hz |
| 记录时长 | 每人 14 个 run：2×1 分钟基线（睁眼/闭眼）+ 12×2 分钟任务 run，单人合计约 28 分钟 |
| 数据格式 | EDF+（每 run 一个 .edf）+ .event 注释文件；未压缩总量约 3.4 GB |
| 任务范式 | ① 睁眼静息基线 ② 闭眼静息基线 ③-⑭ 左/右拳运动执行、左/右拳运动想象、双拳/双脚运动执行、双拳/双脚运动想象（视觉提示触发） |
| 标注情况 | EDF+ 内嵌注释通道：T0=静息、T1=左拳（或双拳）、T2=右拳（或双脚）；具体语义随 run 类型变化 |
| 许可证 | Open Data Commons Attribution License v1.0（**ODC-By**） |
| AI 训练 | ✅ 允许（含商业用途），须署名引用 |
| 下载方式 | ① ZIP 直链（1.9 GB）② `wget -r -N -c -np https://physionet.org/files/eegmmidb/1.0.0/` ③ `aws s3 sync --no-sign-request s3://physionet-open/eegmmidb/1.0.0/` —— **三种方式均无需注册** |
| 引用要求 | Schalk (2009), PhysioNet + Goldberger (2000), Circulation + Schalk (2004), IEEE TBME |

**特点**：经典 BCI 基准数据集，文献引用量极大；运动区（C3/C4/CP 区域）信号丰富，前额通道齐全但非研究重点；每 run 仅 1-2 分钟，适合按 run 切片喂给引擎的 4 秒分析窗口。

---

### 2.2 OpenNeuro ds008108 — OSA 认知障碍多模态数据集

**全名**：A Comprehensive Multimodal Dataset for Investigating Cognitive Impairment in Obstructive Sleep Apnea
**主页**：<https://openneuro.org/datasets/ds008108/versions/1.0.0> ｜ GitHub：<https://github.com/OpenNeuroDatasets/ds008108>
**DOI**：[10.18112/openneuro.ds008108.v1.0.0](https://doi.org/10.18112/openneuro.ds008108.v1.0.0) ｜ 发布：2026-07-07 ｜ 贡献：Wei Guo et al.（大连理工大学生物医学工程学院 + 附属中心医院）

| 元信息项 | 内容 |
|---|---|
| 受试者数 | 142 名（OSA 患者 + 匹配健康对照） |
| 通道数 | PSG 12 通道：E1:M2、E2:M2（眼电）+ **F3:M2、F4:M1、C3:M2、C4:M1、O1:M2、O2:M1**（6 EEG 导联，乳突参考）+ ECG、Chin（下颌肌电）、SPO2、Pulse |
| 前额通道 | ❌ 无 Fp1/Fp2/AF3/AF4；额叶仅 F3/F4（源自 eeg.json 的 ChannelNames 实测确认） |
| 采样率 | 256 Hz（PowerLineFrequency 50 Hz，EpochLength 30 秒） |
| 记录时长 | 5 个 session 纵向设计：ses-preSleep（晚间基线认知）→ ses-nightSleep（**整夜 PSG**）→ ses-postSleep（晨起认知）→ ses-preNap（午后小睡前认知）→ ses-postNap（小睡后认知 + MRI） |
| 数据格式 | EDF（BIDS 标准目录）+ 行为 .tsv + 问卷 + T1w/rs-fMRI MRI |
| 任务范式 | 睡眠（整夜多导睡眠图）+ 4 项连续认知评估：**PPT**（图片配对）、**SART**（持续注意力反应任务）、**MST**（运动技能）、**PVT**（精神运动警觉） |
| 标注情况 | events.tsv（30 秒 epoch 睡眠分期相关事件）+ 行为数据（反应时/错误率）+ 问卷（sourcedata/questionnaires） |
| 许可证 | **CC0**（公有领域奉献） |
| AI 训练 | ✅ 无任何限制 |
| 下载方式 | OpenNeuro 网页/CLI 匿名下载（无需注册）；GitHub DataLad 克隆（大文件走 git-annex） |
| 引用要求 | 请引用 Dataset DOI 及配套描述论文 |

**特点**：对 MedSignal 价值极高——① 整夜 PSG 含完整睡眠周期与 30s epoch 分期，是"睡眠质量指数（δ+θ 占比）"唯一可落地的真实验证源；② OSA 患者 vs 健康对照的分组设计，恰好对应引擎的"脑血管风险预警/认知衰退风险"赛道 7 指标（OSA 是脑血管病公认危险因素）；③ SART/PVT 行为数据可交叉校验"注意力指数"；④ 采样率 256 Hz 与引擎默认完全一致。**短板**：EEG 为临床导联制（F3:M2 等），无前额 Fp/AF 通道，接入时需做通道名解析与映射。

---

### 2.3 OpenNeuro ds008496 — Gen-AI 学生学习过程数据集

**全名**：Brain Connectivity Based on EEG of Student Learning Processes Using Gen-AI
**主页**：<https://openneuro.org/datasets/ds008496/versions/1.0.1> ｜ GitHub：<https://github.com/OpenNeuroDatasets/ds008496>
**DOI**：[10.18112/openneuro.ds008496.v1.0.1](https://doi.org/10.18112/openneuro.ds008496.v1.0.1) ｜ 发布：2026-07-28 ｜ 贡献：Achmad Imam Kistijantoro et al.（印尼 ITB 等机构联合）

| 元信息项 | 内容 |
|---|---|
| 受试者数 | 15 名（20-22 岁大学生，8 男 7 女） |
| 通道数 | 14 通道 EEG + 44 个 MISC 通道（时间戳、CQ 信号质量、电池、Marker 等），共 58 列（源自 channels.tsv 实测确认） |
| 电极布局 | **Emotiv EPOC X**：AF3、F7、F3、FC5、T7、P7、O1、O2、P8、T8、FC6、F4、F8、AF4（CMS/DRL 参考） |
| 前额通道 | ✅ AF3、AF4（**与 device_adapter.py 的 CHANNEL_MAP 现有映射完全对应**） |
| 采样率 | **256 Hz**（与引擎 SAMPLE_RATE 完全一致） |
| 记录时长 | 每 tasks 约 39 分钟（sub-001 activeai 实测 2348 秒）；每人 2 个任务（passiveai / activeai） |
| 数据格式 | **EEGLAB .set + .fdt**（BIDS 目录，需 MNE-Python 或 EEGLAB 读取） |
| 任务范式 | 不同 AI 交互条件下的写作任务：passiveai（AI 主导）/ activeai（主动创作），评估创造力、记忆、批判性思维 |
| 标注情况 | events.tsv + task-{activeai,passiveai}_events.json；内置逐通道信号质量（CQ_*）与硬件 Marker 通道 |
| 许可证 | **CC0** |
| AI 训练 | ✅ 无任何限制 |
| 下载方式 | OpenNeuro 网页/CLI 匿名下载；GitHub DataLad 克隆 |
| 引用要求 | 请引用 Dataset DOI |

**特点**：与 MedSignal 契合度惊人的高——① 采集设备 Emotiv EPOC X 正是项目文档《EEG设备接入指南》中列明支持的消费级设备，数据真实性背书强；② 256Hz + AF3/AF4 前额通道，引擎的 CHANNEL_MAP 已内置 `AF3→AF7、AF4→AF8` 映射；③ "AI 辅助 vs 主动创作"的对照设计直接对应"认知负荷（β+γ）"与"注意力（θ/β）"指标的验证需求——**有 AI 辅助时认知负荷应下降**是可检验的假设；④ 自带逐通道信号质量标注，可用于验证 `_assess_quality()` 质量评估函数。**短板**：受试者仅 15 人，统计功效有限；EEGLAB 格式需新增读取依赖。

---

### 2.4 OpenNeuro ds007955 — 情绪词联想数据集

**全名**：EEG and autonomic responses during emotional word association
**主页**：<https://openneuro.org/datasets/ds007955/versions/1.0.0> ｜ GitHub：<https://github.com/OpenNeuroDatasets/ds007955>
**DOI**：[10.18112/openneuro.ds007955.v1.0.0](https://doi.org/10.18112/openneuro.ds007955.v1.0.0) ｜ 发布：2026-06-10 ｜ 贡献：Manuel Cebral-Loureda et al.（墨西哥，SECIHTI Ciencia de Frontera 2023 资助）

| 元信息项 | 内容 |
|---|---|
| 受试者数 | 9 名（sub-01 ~ sub-09，匿名化） |
| 通道数 | 8 通道 EEG |
| 电极布局 | **OpenBCI Cyton + Ultracortex Mark IV**：Fp1、Fp2、F3、F4、P7、P8、O1、O2（双耳耳夹参考，A1/A2） |
| 前额通道 | ✅ Fp1、Fp2（前额极点，情绪不对称性分析的标准电极） |
| 采样率 | 250 Hz（PowerLineFrequency 60 Hz） |
| 记录时长 | 每人单次任务约 3 分钟（单 session） |
| 数据格式 | **EEGLAB .set**（BIDS 目录） |
| 任务范式 | 情绪词汇联想：呈现与"恐惧"相关的情绪词汇，受试者选择建议词或自创新词（wordassociation 任务） |
| 标注情况 | events.tsv 字段：onset、duration、trial_type、Word（所选/所造词）、**Correlation（相邻词语义相似度）**、NewWord（自创/选择标记） |
| 附加模态 | Empatica E4 腕带：**EDA（皮肤电）**、BVP（血容量脉搏）、IBI（心跳间期）、皮温（sub-07 生理数据缺失） |
| 许可证 | **CC0** |
| AI 训练 | ✅ 无任何限制 |
| 下载方式 | OpenNeuro 网页/CLI 匿名下载；GitHub DataLad 克隆 |
| 引用要求 | 引用 DOI 及配套论文（含 Front. Hum. Neurosci. 2024 实时 EEG 情绪识别论文） |

**特点**：四个数据集中唯一带**明确情绪诱发范式**（恐惧相关词汇）且同步采集**自主神经信号（EDA）**的数据集——EDA 是情绪唤醒度的经典生理金标准，可与引擎的 emotion_arousal 指标做外部一致性校验；配套发表的实时情绪识别论文（PCA + 树模型）提供了方法学参照。Fp1/Fp2 是前额 α 不对称性（引擎情绪 valence 计算的临床依据）的标准电极。**短板**：9 人 × 3 分钟，数据量最小，仅适合概念验证（PoC）与指标趋势验证，不足以支撑模型训练。

---

## 三、与 MedSignal 五维指标的适配性分析

### 3.1 引擎指标计算逻辑回顾

本地引擎（`backend/app/services/eeg/engine.py`）基于五频段平均功率（Welch PSD：δ 0.5-4Hz / θ 4-8Hz / α 8-13Hz / β 13-30Hz / γ 30-45Hz）计算：

| 指标 | 计算依据 | 生理学依据 |
|---|---|---|
| 压力指数 | α/β 比值反演 | α 高 β 低 = 放松；α 抑制 β 亢进 = 紧张 |
| 注意力指数 | θ/β 比值反演 | θ 低 β 高 = 专注（θ/β 比值是 ADHD 脑电经典标志物） |
| 睡眠质量 | δ+θ 慢波占比 | 慢波充足 = 睡眠好 |
| 认知负荷 | β+γ 快波占比 | 高频活动 = 高认知消耗 |
| 情绪状态 | valence（α/β 效价）+ arousal（β+γ 唤醒） | 前额 α 不对称性 + β 活跃度（DEAP/SEED 范式） |

### 3.2 适配性矩阵

评级说明：★★★ 理想验证源 ／ ★★ 可有效验证 ／ ★ 间接/参考性验证 ／ — 不适用

| MedSignal 指标 | eegmmidb | ds008108 | ds008496 | ds007955 | 说明 |
|---|:---:|:---:|:---:|:---:|---|
| **压力指数**（α/β） | ★ | ★ | ★★ | ★★ | ds008496：写作时间压力 vs AI 减负；ds007955：恐惧词汇诱发急性应激（可叠加 EDA 佐证）；eegmmidb：任务 vs 静息的 β 差异可作弱对照 |
| **注意力指数**（θ/β） | ★ | ★★★ | ★★ | — | ds008108：**SART 持续注意力任务 + PVT 警觉性任务有逐试次行为数据**（反应时/失误率），是唯一可用行为绩效交叉校验脑电注意力的数据集；ds008496：持续写作的注意力维持 |
| **睡眠质量**（δ+θ） | ★ | ★★★ | — | — | ds008108 **唯一选择**：整夜 PSG 覆盖完整睡眠周期（N1/N2/N3/REM），30s epoch 分期标注 + OSA 组间对照（OSA 患者睡眠质量应显著差于对照组——直接可检验）；eegmmidb 闭眼基线可验证 α 波增强，与睡眠无关 |
| **认知负荷**（β+γ） | ★ | ★★ | ★★★ | — | ds008496 **理想**：activeai vs passiveai 是"AI 辅助降低认知负荷"的天然 A/B 对照实验；ds008108：认知任务前后（preSleep vs postSleep 睡眠剥夺效应）；eegmmidb：运动执行 vs 想象的激活差异（与认知负荷语义不匹配） |
| **情绪状态**（valence/arousal） | — | — | ★ | ★★★ | ds007955 **唯一选择**：恐惧情绪诱发范式 + Fp1/Fp2 前额 α 不对称性电极 + EDA 唤醒度外部校验 + 情绪识别论文背书；ds008496：创造过程的积极情绪（弱） |
| **附加：脑血管/认知衰退风险** | — | ★★★ | — | — | ds008108：OSA 是脑血管病与认知障碍的公认危险因素，142 人患者-对照分组完美对应赛道 7 预警指标的病理学验证 |
| **附加：引擎 sanity check** | ★★★ | — | — | — | eegmmidb 闭眼 vs 睁眼基线：闭眼枕区 α 显著增强是教科书级神经生理现象，可用于验证引擎 PSD 管线的正确性 |

### 3.3 分指标最佳验证组合

- **压力** → ds008496（慢性认知压力）+ ds007955（急性情绪应激，EDA 佐证）
- **注意力** → ds008108（SART/PVT 行为绩效交叉校验，金标准）
- **睡眠** → ds008108（整夜 PSG + 睡眠分期，唯一解）
- **认知负荷** → ds008496（AI 辅助 A/B 对照，设计最贴合）
- **情绪** → ds007955（情绪诱发 + 前额 Fp1/Fp2，唯一解）

---

## 四、接入优先级推荐

综合**下载便利性 × 前额通道可用性 × 与压力/注意力指标相关性 × 工程改造成本**四个维度：

### 🥇 P0-A（第一批首选）：ds008496 — Gen-AI 学生学习数据集

**推荐理由：**
1. **参数零距离**：256 Hz 采样率与引擎 `SAMPLE_RATE=256` 完全一致，无需重采样；AF3/AF4 前额通道，`device_adapter.py` 的 `CHANNEL_MAP` 已内置 `AF3→AF7 / AF4→AF8` 映射，接入即走现有通道映射逻辑。
2. **指标强相关**：activeai/passiveai 双条件直接验证"认知负荷 + 注意力 + 压力"三个核心指标（AI 辅助 → 认知负荷下降、压力缓解是可量化检验的假设）。
3. **真实性背书**：Emotiv EPOC X 是项目《EEG设备接入指南》明文支持的消费级设备，"用 Emotiv 公开数据验证 Emotiv 接入管线"叙事完整，路演/答辩说服力强。
4. **自带信号质量标注**（CQ_* 通道）：可反向验证引擎 `_assess_quality()` 的质量判定准确性。
5. **规模适中**：15 人 × 2 任务 × ~39 分钟，处理成本可控。

**接入成本**：需新增 EEGLAB `.set/.fdt` 读取能力（`pip install mne`，用 `mne.io.read_raw_eeglab`，或离线转 EDF/CSV 后零依赖接入）。

### 🥈 P0-B（第一批并行）：ds008108 — OSA 认知障碍多模态数据集

**推荐理由：**
1. **睡眠指标唯一解**：整夜 PSG + 30s epoch 分期，142 人临床级样本，是"睡眠质量指数"从合成走向真实验证的必经之路。
2. **临床叙事升级**：OSA 患者 vs 健康对照分组，直接支撑"脑血管风险预警 / 认知衰退风险"赛道 7 指标的病理学验证——这是医保联动故事的核心证据链。
3. **行为数据交叉校验**：SART/PVT 逐试次反应时数据可检验"注意力指数"的行为效度（脑电指标 ↔ 行为绩效相关性分析）。
4. **格式零改造**：EDF 格式直接走现有 `load_from_edf()`（pyedflib），`target_channels=["F3","F4","O1","O2"]` 的模糊匹配可命中 "F3:M2" 等导联名。
5. **256 Hz**：与引擎一致。

**接入成本**：① 通道为导联制（"F3:M2"），需在通道解析层做名称清洗；② 无前额通道，压力/情绪类前额指标在该数据集上只能用 F3/F4 额叶代理；③ 数据量大（整夜 PSG × 142 人），建议抽样接入（如先取 10-20 名受试者的 N3 深睡段 + REM 段）。

### 🥉 P1（第二批）：ds007955 — 情绪词联想数据集

**推荐理由：**
1. **情绪指标唯一解**：恐惧情绪诱发范式 + Fp1/Fp2（前额 α 不对称性标准电极）+ EDA 皮肤电唤醒度校验 + 情绪识别论文方法学参照。
2. **多模态联动叙事**：EEG 情绪 valence/arousal ↔ EDA 生理唤醒的一致性分析，可作为"多模态健康画像"的技术亮点。
3. **CC0 + 轻量**：9 人 × 3 分钟，下载与处理成本几乎为零。

**限制**：样本量小（n=9），仅作概念验证与指标趋势验证；250 Hz 与引擎默认不同（引擎 `extract_band_powers` 支持任意采样率参数，直接传入即可，无需重采样——但需注意合成器默认 256Hz 的叙事一致性）；EEGLAB `.set` 格式（与 ds008496 共用同一套读取改造）。

### 🏅 P2（第三批/资源型）：eegmmidb — 运动执行/想象数据集

**推荐理由：**
1. **下载最便利**：直链 ZIP / wget / AWS S3，三种方式全部免注册，网络受限环境（如比赛现场）最稳。
2. **管线压力测试**：109 人 × 64 通道 × 14 run 的大规模 EDF 批处理，是检验接入管线吞吐与健壮性的理想负载。
3. **引擎 sanity check**：闭眼 vs 睁眼基线 run——闭眼后顶枕区 α 波显著增强是教科书级现象，可用于验证引擎 PSD/频段积分实现的正确性（预期结果：闭眼 run 的 α 功率显著高于睁眼 run）。

**限制**：160 Hz 需注意频段计算参数（引擎支持任意采样率，但 γ 频段上限 45Hz < 80Hz 奈奎斯特频率，无碍）；运动想象范式与五维指标相关性弱，不建议作为指标验证主力；1.9GB 下载体量偏大。

### 优先级总评

```
ds008496 ──┬─ P0（认知负荷/注意力/压力主线，参数同构，叙事完整）
ds008108 ──┘    （睡眠/脑血管风险主线，临床样本，EDF 零改造）
ds007955 ─── P1（情绪主线，PoC 级验证，多模态亮点）
eegmmidb ─── P2（工程压测 + 引擎 sanity check，下载最便利）
```

---

## 五、本地 EEG 引擎现状（代码勘察）

### 5.1 关键文件

| 文件 | 职责 |
|---|---|
| `backend/app/services/eeg/engine.py` | 分析引擎：合成信号生成 → Welch PSD 频域特征 → 五维健康指标 → 异常预警 → 医保政策联动 |
| `backend/app/services/eeg/device_adapter.py` | 设备适配层：LSL / CSV / EDF / NumPy 四种信号来源统一为 `(signals, channels, sample_rate)` 三元组 |
| `backend/app/routers/eeg.py` | FastAPI 路由（前缀 `/api/eeg`），9 个端点 |
| `backend/app/services/eeg/__init__.py` | 模块导出（引擎核心 + 设备适配全部公开符号） |

### 5.2 引擎的信号格式要求（真实数据接入契约）

```python
# 统一信号三元组（device_adapter.py 所有加载函数的返回值）
signals:     list[np.ndarray]   # 每个元素是一个通道的信号（float64，单位 μV）
channels:    list[str]          # 通道名列表
sample_rate: int                # 采样率 Hz

# 引擎常量
SAMPLE_RATE    = 256                       # 默认采样率
CHANNELS       = ["TP9", "AF7", "AF8", "TP10"]   # Muse 4 通道布局
WINDOW_SECONDS = 4                         # 分析窗口 4 秒（1024 点）
BANDS          = {delta: (0.5, 4), theta: (4, 8), alpha: (8, 13),
                  beta: (13, 30), gamma: (30, 45)}
```

**真实数据评估入口**（v2.2 已具备，真实数据集接入的关键复用点）：

```python
assess_real_session(user_id, signals, channels, sample_rate,
                    mental_state="auto", user_profile=None, device_info=None)
# 流程：真实信号 → extract_band_powers → compute_health_metrics
#       → scan_eeg_alerts → link_to_policies → EEGSession(source="file"/"device")
# mental_state="auto" 时按 α/β/θ/δ 比值自动推断心理状态
```

**通道映射**（`CHANNEL_MAP`，与 Emotiv 数据直接相关）：
`AF3→AF7`、`AF4→AF8`（Emotiv EPOC 布局已预置映射）；`_map_channels()` 策略：命中 Muse 布局名优先返回，否则取前 4 通道以 `TP9/AF7/AF8/TP10` 命名。

**信号质量评估**（`_assess_quality()`）：峰峰值幅度（正常 10-100μV）、50Hz 工频占比、方差 → good/fair/poor 三级。

### 5.3 合成信号生成器输出格式

`generate_synthetic_eeg(mental_state, duration_seconds, sample_rate, channels)` 返回 `(signals, channels, sample_rate)`：
- 5 种心理状态预设（relaxed/focused/stressed/fatigued/sleep_deprived），每种定义五频段振幅权重；
- 信号 = 多频段正弦叠加（δ 1/2/3Hz、θ 5/6/7Hz、α 9/10/11Hz、β 15/20/25Hz、γ 35/40Hz）+ 50Hz 工频 + 白噪声 + 0.1Hz 缓慢漂移。

**结论：合成器与分析引擎之间只通过 `(signals, channels, sample_rate)` 三元组耦合**——真实数据集只要落进这个三元组契约（任何采样率、任何通道数 ≤ 经 `_map_channels` 归一为 4 通道），即可完整复用 `extract_band_powers → compute_health_metrics → scan_eeg_alerts → link_to_policies` 全链路，无需修改引擎核心。

### 5.4 EEG API 端点清单（`/api/eeg` 前缀）

| 方法 | 端点 | 说明 | 请求 | 响应核心字段 |
|---|---|---|---|---|
| GET | `/api/eeg/states` | 心理状态列表 | — | `states[]`（key/label/五维参考分）、`channels`、`sample_rate` |
| POST | `/api/eeg/{user_id}/session` | 合成信号会话评估 | Query: `mental_state=auto`、`duration_seconds=4`(1-30) | `EEGSession.to_dict()`：metrics（五维+ratios+赛道7）、alerts、policy_links、waveform、band_powers |
| GET | `/api/eeg/{user_id}/latest` | 最近一次评估 | — | 同上 + `from_history` |
| GET | `/api/eeg/{user_id}/history` | 历史趋势 | Query: `limit=20` | `history[]`、`trend[]`（四维时序） |
| GET | `/api/eeg/{user_id}/realtime` | 实时数据块（轮询） | Query: `mental_state`、`seed` | `waveform[]`、`band_powers`、`metrics_snapshot` |
| GET | `/api/eeg/{user_id}/policy-links` | 医保政策联动 | — | `policy_links[]` |
| GET | `/api/eeg/device/check` | LSL 设备探测 | — | `connected`、`device_name`、`channels` |
| POST | `/api/eeg/{user_id}/session-device` | LSL 真实设备采集评估 | Query: `duration_seconds`、`mental_state` | 同 session |
| **POST** | **`/api/eeg/{user_id}/import`** | **文件导入分析（数据集接入主通道）** | **multipart: `file`（.csv/.edf/.txt）+ Query: `sample_rate=256`（CSV/TXT 必填，EDF 自动）、`mental_state=auto`** | 同 session |

**`/import` 是公开数据集接入的天然入口**：数据集文件转成 EDF 或 CSV 后即可直接上传走现有管线；响应中的 `source="file"`、`device_info`（含 `device_name`=文件名、`signal_quality`）已具备数据集溯源能力。

### 5.5 依赖现状（`backend/requirements.txt`）

- 已有：`numpy>=1.26.0`（PSD 计算自实现，无 scipy 依赖）
- 可选注释态：`pylsl`（LSL 实时流）、`pyedflib`（EDF 解析）——**接入 ds008108/eegmmidb 前需 `pip install pyedflib`**
- 缺失：EEGLAB `.set/.fdt` 读取依赖（ds008496/ds007955 需要 `mne`，或预先离线转换格式）

---

## 六、接入技术方案建议

### 6.1 数据流路径（推荐：离线转换 + 现有 import API）

```
公开数据集 ──下载──> 本地缓存 ──离线预处理脚本──> EDF/CSV 中间格式
                                                      │
                        ┌─────────────────────────────┤
                        ▼                             ▼
            POST /api/eeg/{uid}/import        离线批处理脚本
            （演示/API 演示用）               （直接调 assess_real_session，
                                              结果走 crud.create_eeg_record 入库）
```

### 6.2 各数据集的转换要点

| 数据集 | 原始格式 | 转换方案 | 目标通道选择建议 |
|---|---|---|---|
| ds008108 | EDF（BIDS） | **零转换**，`load_from_edf(path, target_channels=["F3","F4","O1","O2"])` 直接可用（模糊匹配可命中 "F3:M2"） | F3/F4（额叶，压力/认知代理）+ O1/O2（枕区，睡眠 α 验证）；切 30s epoch 对齐睡眠分期 |
| eegmmidb | EDF+ | 零转换，`load_from_edf` 直接可用 | Fp1/Fp2/AF3/AF4（前额）或 C3/C4；先做睁眼/闭眼 run 的 α 对比 sanity check |
| ds008496 | EEGLAB .set+.fdt | `mne.io.read_raw_eeglab()` → 保留 14 EEG 通道 → 存 EDF（`mne.io.Raw.save(fmt='edf')`）或 CSV | AF3/AF4（引擎已有映射）+ F3/F4；剔除 44 个 MISC 通道与 CQ_* 通道 |
| ds007955 | EEGLAB .set | 同上（mne 读取 → EDF/CSV） | Fp1/Fp2（情绪不对称性）+ F3/F4 |

### 6.3 需要的代码改动（最小集）

1. **新增 EEGLAB 读取适配**（P0-A 必需）：在 `device_adapter.py` 增加 `load_from_eeglab()`（依赖 `mne`，同样返回统一三元组），或提供 `scripts/convert_eeglab_to_edf.py` 离线转换脚本（零运行时依赖）。
2. **通道名清洗**（P0-B 必需）：ds008108 的导联名 "F3:M2" 含参考电极后缀，建议在 `load_from_edf` 前做 `label.split(":")[0]` 归一化，或在 `target_channels` 匹配层处理（现有模糊匹配已能命中，但返回的 `channels_raw` 会带后缀）。
3. **切片与分段**：真实数据集动辄数十分钟，而 `/import` 端点无时长限制（引擎内部 `extract_band_powers` 对任意长度信号自适应，`nperseg=min(256,n)`），建议离线脚本按 30s 或 60s 分段逐段评估，输出指标时序曲线（可与 ds008108 睡眠分期对齐画图）。
4. **批处理入库**：复用 `crud.create_eeg_record()`，`mental_state` 建议传 "auto"（引擎将按频段比值自动归类），并在 `device_info` 中记录 `{dataset: "ds008108", subject: "sub-001", session: "ses-nightSleep"}` 实现数据集溯源。

### 6.4 已发现的两个技术注意点（勘察结论）

1. **`extract_band_powers` 的通道名硬编码**：`engine.py` 第 309 行 `ch_name = CHANNELS[i] if i < len(CHANNELS) else f"ch{i+1}"` 使用全局 Muse 布局命名而非传入的 channels——经 `device_adapter` 归一为 ≤4 通道时无影响，但若绕过适配层直接传入 >4 通道数据（如 ds008496 的 14 通道），`band_powers` 字典的通道名会错位。接入脚本应先经 `_map_channels`（或 `from_numpy()`）截取 4 通道。
2. **`_map_channels` 的重命名副作用**：非 Muse 布局的前 4 通道会被统一改名为 TP9/AF7/AF8/TP10（如 ds008108 的 F3/F4/O1/O2）——对指标计算无影响（指标只用跨通道平均功率），但报告展示层若要显示真实电极名，需在 `device_info.channels` 中保留原始通道名。

### 6.5 建议的验证实验设计（接入后即可执行）

| 实验 | 数据 | 预期结果 | 验证目标 |
|---|---|---|---|
| E1 闭眼 α 增强 | eegmmidb R02（闭眼）vs R01（睁眼） | 闭眼 run α 功率显著更高 | PSD 管线正确性 |
| E2 睡眠分期对应 | ds008108 夜间 PSG，N3 vs REM 段 | N3 段 δ+θ 占比与睡眠质量指数显著高于 REM/清醒 | 睡眠质量指标效度 |
| E3 OSA 组间差异 | ds008108 OSA 组 vs 对照组整夜 | OSA 组睡眠质量/认知衰退风险指标更差 | 赛道 7 预警指标病理学效度 |
| E4 AI 减负效应 | ds008496 activeai vs passiveai | passiveai（AI 主导）认知负荷指数更低 | 认知负荷指标效度 |
| E5 情绪唤醒联动 | ds007955 恐惧词诱发段 vs 静息 | EEG arousal 指标与 EDA 同步升高 | 情绪指标外部效度 |
| E6 注意力行为校验 | ds008108 SART/PVT 试次 | 注意力指数与反应时/失误率负相关 | 注意力指标行为效度 |

---

## 七、许可证与引用合规

| 数据集 | 许可证 | 商用 | AI 训练 | 义务 |
|---|---|---|---|---|
| eegmmidb | ODC-By 1.0 | ✅ | ✅ | 署名（引用 Schalk 2009 + Goldberger 2000 + BCI2000 论文） |
| ds008108 | CC0 | ✅ | ✅ | 无法律义务，建议学术礼节性引用 DOI |
| ds008496 | CC0 | ✅ | ✅ | 同上 |
| ds007955 | CC0 | ✅ | ✅ | 同上（建议引用 Front. Hum. Neurosci. 2024 论文） |

**结论：四个数据集全部允许 AI 训练与商业用途**，MedSignal（医疗 AI 比赛项目）接入无合规障碍。建议在项目申报书/答辩材料的数据来源声明中统一列出四个 DOI。

---

## 附录：下载命令汇总

```bash
# ── 1. PhysioNet eegmmidb（免注册直链）──────────────────────
# 方式 A：ZIP 直链（1.9 GB）
wget https://physionet.org/content/eegmmidb/get-zip/1.0.0/
# 方式 B：递归下载（可断点续传）
wget -r -N -c -np https://physionet.org/files/eegmmidb/1.0.0/
# 方式 C：AWS S3（免签名）
aws s3 sync --no-sign-request s3://physionet-open/eegmmidb/1.0.0/ ./eegmmidb

# ── 2. OpenNeuro ds008108（CC0，匿名下载）───────────────────
# 方式 A：网页 Download 按钮（无需登录）
#   https://openneuro.org/datasets/ds008108/versions/1.0.0/download
# 方式 B：DataLad / git-annex 克隆
datalad clone https://github.com/OpenNeuroDatasets/ds008108.git
cd ds008108 && datalad get sub-001   # 按需拉取受试者

# ── 3. OpenNeuro ds008496（CC0，匿名下载）───────────────────
#   https://openneuro.org/datasets/ds008496/versions/1.0.1/download
datalad clone https://github.com/OpenNeuroDatasets/ds008496.git

# ── 4. OpenNeuro ds007955（CC0，匿名下载）───────────────────
#   https://openneuro.org/datasets/ds007955/versions/1.0.0/download
datalad clone https://github.com/OpenNeuroDatasets/ds007955.git

# ── 接入依赖安装 ────────────────────────────────────────────
pip install pyedflib    # EDF 解析（ds008108 / eegmmidb）
pip install mne         # EEGLAB .set 解析（ds008496 / ds007955）
```

---

## 参考链接

- PhysioNet eegmmidb：<https://physionet.org/content/eegmmidb/1.0.0/>（DOI: 10.13026/C28G6P）
- OpenNeuro ds008108：<https://openneuro.org/datasets/ds008108/versions/1.0.0>（DOI: 10.18112/openneuro.ds008108.v1.0.0）
- OpenNeuro ds008496：<https://openneuro.org/datasets/ds008496/versions/1.0.1>（DOI: 10.18112/openneuro.ds008496.v1.0.1）
- OpenNeuro ds007955：<https://openneuro.org/datasets/ds007955/versions/1.0.0>（DOI: 10.18112/openneuro.ds007955.v1.0.0）
- 本地代码：`backend/app/services/eeg/engine.py`、`backend/app/services/eeg/device_adapter.py`、`backend/app/routers/eeg.py`

*报告完 — 生成于 2026-08-27，数据集元信息以各官方页面及 BIDS 元数据文件（channels.tsv / eeg.json，经 GitHub 原始文件实测核验）为准。*
