# 3D 解剖模型来源与许可

viewer 的真实人体 3D 模型来自两个开源项目，本文档记录来源、版本、许可与本地路径。

## 女性：HuBMAP Human Reference Atlas — Visible Human Female 器官库

同源同许可（CC BY 4.0，v1.3），用于患者 `sex=f` 时切换。

- **本地路径**：`backend/app/static/digital-body/models/VH_F_*.glb` / `SBU_F_Intestine_Large.glb`
- **列表**（共 17 个，约 38 MB）：Heart / Lung / Liver / Kidney_L+R / Spleen / Pancreas / Small_Intestine / Intestine_Large / Spinal_Cord / Pelvis / Knee_L+R / Blood_Vasculature / **Uterus 子宫** / **Ovary_L+R 卵巢**

> **女性皮肤外壳**：HuBMAP 未发布独立 `VH_F_Skin.glb`（v2.0 的 `3d-vh-f-united.glb.7z` 78MB 含完整女性但体积过大），本技能复用男性皮肤（`VH_M_Skin.glb`）。CCF 统一坐标系下两套器官位置相近，可大致对齐。如要纯女性外形，下载 united 7z、提取为 `VH_F_Skin.glb`，再把 `backend/app/static/digital-body/index.html` 中 `SKIN_FILE.f` 改为对应路径。

## 主体：HuBMAP Human Reference Atlas — Visible Human Male 器官库

- **来源仓库**：[hubmapconsortium/ccf-releases](https://github.com/hubmapconsortium/ccf-releases)
- **使用版本**：v1.3（`v1.3/models/`），CCF Release 6
- **许可**：[Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **原始数据**：基于美国国家医学图书馆 Visible Human Project 男性数据集（1803 mm 高，38 岁）
- **下载链接格式**：`https://raw.githubusercontent.com/hubmapconsortium/ccf-releases/main/v1.3/models/<文件名>.glb`

### 本地路径

| 器官 key | 文件 | 大小 | 网格数 |
|---|---|---:|---:|
| skin（外壳） | `backend/app/static/digital-body/models/VH_M_Skin.glb` | 5.9 MB | 1 |
| heart | `VH_M_Heart.glb` | 4.0 MB | 14 |
| lungs | `VH_M_Lung.glb` | 6.4 MB | 67 |
| liver | `VH_M_Liver.glb` | 1.1 MB | 26 |
| kidneys | `VH_M_Kidney_L.glb` + `VH_M_Kidney_R.glb` | 1.5 + 1.5 MB | 22 + 24 |
| spleen | `VH_M_Spleen.glb` | 0.5 MB | 5 |
| pancreas | `VH_M_Pancreas.glb` | 0.3 MB | 5 |
| intestines | `VH_M_Small_Intestine.glb` + `SBU_M_Intestine_Large.glb` | 0.6 + 0.7 MB | 10 + 10 |
| spine | `VH_M_Spinal_Cord.glb` | 0.5 MB | 30 |
| pelvis | `VH_M_Pelvis.glb` | 1.3 MB | 14 |
| knee_l / knee_r | `VH_M_Knee_L.glb` / `VH_M_Knee_R.glb` | 0.4 MB each | 20 + 20 |
| vasculature（图层） | `VH_M_Blood_Vasculature.glb` | 7.4 MB | 104 |

男性模型合计约 35 MB，男女与骨骼资源合计约 70 MB，均位于 `backend/app/static/digital-body/models/`。

### 缺失的器官

以下常见器官 CCF v1.3 未提供独立 GLB，viewer 改为按身体比例定位标记球（PROPORTION_ORGANS）：

- brain（脑）— 用 Allen_M_Brain.glb（12 MB）即可加入，目前未引入以保持包体小
- neck（颈）、chest（胸）、abdomen（腹）
- stomach（胃）— HuBMAP 未提供；附近无合适替代
- shoulder_l / shoulder_r（左/右肩）
- arm_l / arm_r、leg_l / leg_r
- prostate（前列腺）— 男性，无 GLB，按身体比例定位

如需接入胃或脑的 GLB，修改 `backend/app/static/digital-body/index.html` 中的模型注册表与 `PROPORTION_ORGANS`，锚点会从 GLB 包围盒重算。

### 版权声明

使用本 viewer 即同意对上述 HuBMAP HRA 模型保留 CC BY 4.0 归属要求。若二次分发，请附：
> Anatomical reference objects courtesy of the Human Reference Atlas, supported by NIH Common Fund through the HuBMAP program (OT2OD026671).

## 骨骼图层：Open3DModel / Caskanatomy

- **来源**：[anatomytool.org/open3dmodel-create](https://anatomytool.org/open3dmodel-create)
- **文件**：`overview-skeleton-glb.zip` → 解压后 `overview-skeleton.glb`（3.4 MB，Draco 压缩）
- **许可**：CC BY-SA 4.0
- **本地路径**：`backend/app/static/digital-body/models/skeleton/overview-skeleton.glb`
- **viewer 集成**：默认隐藏，左下角"图层"面板勾选"骨骼系统"开启

viewer 用 `three/addons/loaders/DRACOLoader.js` + gstatic Draco 1.5.6 解码器处理压缩。

## 加载与归一化

GLB 全部在 CCF 公共参考坐标系（毫米，Y-up）。viewer 流程：

1. 并行加载 12 个器官 GLB（按器官 key 注册）+ 皮肤 + 血管
2. 全部加进 `modelGroup`，调用 `Box3.setFromObject` 算整体包围盒
3. 自动缩放到目标身高 H=3.25、脚底贴 y=-1.75、水平居中
4. 各器官包围盒中心 → `organAnchors[key]`（用于标记球与徽章锚点）
5. 无 GLB 器官 → `PROPORTION_ORGANS` 按 H 比例定位
6. 骨骼图层单独归一化到同一空间，统一显示坐标

任何新接入的 GLB 都能自动归一化，无需手工校准坐标。

## 数据来源责任

3D 模型仅作为解剖位置参考，非临床诊断工具；viewer 中所有面板均明确"非诊断结论"声明。
