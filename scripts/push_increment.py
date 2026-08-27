"""推送增量变更到 GitHub（通过 Git Data API）"""

import base64
import os
import requests

REPO_OWNER = "yigenfeng0707-netizen"
REPO_NAME = "yibao-eeg"
API_BASE = "https://api.github.com"
BRANCH = "main"
TOKEN = os.popen("gh auth token").read().strip()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "yibao-eeg-push",
}

# 变更的文件列表（相对于项目根目录）
CHANGED_FILES = [
    "docs/安装部署指南.md",
    "docs/用户使用手册.md",
    "README.md",
    "backend/app/services/eeg/engine.py",
    "frontend/src/app/eeg/page.tsx",
    "frontend/src/app/page.tsx",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

session = requests.Session()

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
print("📤 创建 blobs...")
tree_items = []
for rel_path in CHANGED_FILES:
    full_path = os.path.join(ROOT, rel_path.replace("/", os.sep))
    content = open(full_path, "rb").read()
    b64 = base64.b64encode(content).decode("ascii")
    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
        headers=HEADERS,
        json={"content": b64, "encoding": "base64"},
        timeout=60,
    )
    resp.raise_for_status()
    sha = resp.json()["sha"]
    tree_items.append({"path": rel_path, "mode": "100644", "type": "blob", "sha": sha})
    print(f"  ✅ {rel_path} ({len(content)} bytes)")

# 3. 创建 tree（基于 parent tree，只覆盖变更文件）
print("🌳 创建 tree...")
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
print("📝 创建 commit...")
commit_msg = """docs: 新增安装部署指南和用户使用手册

- 安装部署指南：本地开发/Docker/云部署三种方式 + 环境变量说明 + 常见问题排查
- 用户使用手册：7 大功能模块操作指南 + 脑电健康评估 + 医保政策联动 + 常见问题
- README 添加文档导航索引
- 修复 EEG 政策联动文件路径（向上 5 层）
- 修复前端 TypeScript 类型错误（MetricRing style prop + ChatResponse 类型断言）"""

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
print("🔄 更新 main 分支...")
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
