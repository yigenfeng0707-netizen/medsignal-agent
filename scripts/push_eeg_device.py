"""推送 EEG 设备接入功能变更到 GitHub（通过 Git Data API）

变更内容：
- 新增 device_adapter.py（LSL/CSV/EDF/NumPy 四源适配层）
- 新增 3 个 API 端点（device/check、session-device、import）
- 新增 39 个单元测试 + 端到端验证脚本
- 新增《EEG 设备接入指南》文档
- 前端增加三种采集模式切换 UI
- engine.py 新增 assess_real_session() + source 标记修复
"""

import base64
import os
import sys
import requests

REPO_OWNER = "yigenfeng0707-netizen"
REPO_NAME = "yibao-eeg"
API_BASE = "https://api.github.com"
BRANCH = "main"
TOKEN = os.popen("gh auth token").read().strip()

if not TOKEN:
    print("✗ 未获取到 GitHub token，请先运行：gh auth login")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "yibao-eeg-push",
}

# 本次变更的文件列表（相对于项目根目录）
CHANGED_FILES = [
    # 新增文件
    "docs/EEG设备接入指南.md",
    "backend/app/services/eeg/device_adapter.py",
    "backend/tests/test_eeg/test_device_adapter.py",
    "scripts/verify_device_integration.py",
    # 修改的文件
    "backend/app/services/eeg/__init__.py",
    "backend/app/services/eeg/engine.py",
    "backend/app/routers/eeg.py",
    "backend/requirements.txt",
    "frontend/src/lib/api.ts",
    "frontend/src/app/eeg/page.tsx",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

session = requests.Session()


def main():
    # 1. 获取当前 main 分支的最新 commit（作为 parent）
    print("📋 获取当前 main 分支 commit...")
    ref_resp = session.get(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
        headers=HEADERS, timeout=30,
    )
    ref_resp.raise_for_status()
    parent_sha = ref_resp.json()["object"]["sha"]
    print(f"  ✅ Parent: {parent_sha}")

    # 获取 parent commit 的 tree sha
    commit_resp = session.get(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits/{parent_sha}",
        headers=HEADERS, timeout=30,
    )
    parent_tree_sha = commit_resp.json()["tree"]["sha"]
    print(f"  ✅ Parent tree: {parent_tree_sha}")

    # 2. 创建变更文件的 blob
    print(f"\n📤 创建 blobs（{len(CHANGED_FILES)} 个文件）...")
    tree_items = []
    for rel_path in CHANGED_FILES:
        full_path = os.path.join(ROOT, rel_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            print(f"  ✗ 文件不存在：{full_path}")
            sys.exit(1)
        with open(full_path, "rb") as f:
            content = f.read()
        b64 = base64.b64encode(content).decode("ascii")
        resp = session.post(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
            headers=HEADERS,
            json={"content": b64, "encoding": "base64"},
            timeout=60,
        )
        if not resp.ok:
            print(f"  ✗ blob 创建失败：{rel_path}")
            print(f"     HTTP {resp.status_code}: {resp.text[:500]}")
            sys.exit(1)
        sha = resp.json()["sha"]
        tree_items.append({"path": rel_path, "mode": "100644", "type": "blob", "sha": sha})
        print(f"  ✅ {rel_path} ({len(content)} bytes)")

    # 3. 创建 tree（基于 parent tree，只覆盖变更文件）
    print("\n🌳 创建 tree...")
    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/trees",
        headers=HEADERS,
        json={"base_tree": parent_tree_sha, "tree": tree_items},
        timeout=120,
    )
    resp.raise_for_status()
    tree_sha = resp.json()["sha"]
    print(f"  ✅ Tree: {tree_sha}")

    # 4. 创建 commit
    print("\n📝 创建 commit...")
    commit_msg = """feat(eeg): 新增真实 EEG 设备接入功能（LSL/CSV/EDF）

## 新增功能

### 后端
- device_adapter.py：四源信号适配层（LSL 实时流 / CSV / EDF / NumPy）
  - 支持 Muse / Emotiv / OpenBCI 等 LSL 兼容设备
  - 通道名映射（Emotiv 14ch / OpenBCI 8ch → Muse 4ch）
  - 信号质量评估（50Hz 工频 + 幅度 + 方差 → good/fair/poor）
- engine.py：新增 assess_real_session()，真实信号复用全部分析逻辑
  - auto 模式根据 α/β/θ/δ 比值推断心理状态
  - source 字段标记信号来源（synthetic/device/file）
- 3 个新 API 端点：
  - GET  /api/eeg/device/check        — LSL 设备探测
  - POST /api/eeg/{user_id}/session-device — 真实设备采集
  - POST /api/eeg/{user_id}/import    — CSV/EDF 文件导入

### 前端
- 脑电页面增加三种采集模式切换 UI（合成信号/真实设备/文件导入）
- 设备检测按钮 + LSL 流列表展示
- 文件选择器 + 采样率选择（256/250/500/1000/220Hz）
- 错误提示与引导

### 测试与验证
- 39 个单元测试（test_device_adapter.py）覆盖全部分支
- 端到端验证脚本（verify_device_integration.py）
- 全部 131 个测试通过，无回归

### 文档
- 《EEG 设备接入指南》覆盖 Muse/Emotiv/OpenBCI + CSV/EDF 导入"""

    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits",
        headers=HEADERS,
        json={"message": commit_msg, "tree": tree_sha, "parents": [parent_sha]},
        timeout=60,
    )
    resp.raise_for_status()
    commit_sha = resp.json()["sha"]
    print(f"  ✅ Commit: {commit_sha}")

    # 5. 更新 main 分支 ref
    print("\n🔄 更新 main 分支...")
    resp = session.patch(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
        headers=HEADERS,
        json={"sha": commit_sha, "force": False},
        timeout=60,
    )
    resp.raise_for_status()
    print(f"  ✅ Ref 更新成功")

    print(f"\n🎉 推送完成！")
    print(f"   仓库: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"   Commit: {commit_sha}")
    print(f"   变更文件: {len(CHANGED_FILES)} 个")
    print(f"   新增文件: 4 个（device_adapter.py / test_device_adapter.py / verify_device_integration.py / EEG设备接入指南.md）")
    print(f"   修改文件: 6 个")


if __name__ == "__main__":
    main()
