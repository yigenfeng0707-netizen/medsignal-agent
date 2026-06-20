"""
通过 GitHub Git Database API 推送 commit（绕过 git protocol 网络问题）

流程：获取 base tree → 创建 blobs → 创建新 tree → 创建 commit → 更新 ref
所有请求走 gh api 通道（已验证可用）。
"""

import base64
import json
import subprocess
import sys
import os
from pathlib import Path

REPO = "yigenfeng0707-netizen/yibao-zhinao"
BRANCH = "master"

# 要推送的文件（相对仓库根目录的路径）
FILES = [
    ".github/workflows/deploy.yml",
    "render.yaml",
    "docs/部署配置清单.md",
]

REPO_ROOT = Path(__file__).resolve().parent.parent  # yibao-zhinao/


def gh_api(method: str, endpoint: str, field: str = None, input_data: str = None):
    """调用 gh api，返回解析后的 JSON 或原始输出"""
    cmd = ["gh", "api", "--method", method, endpoint]
    if field:
        cmd += ["--field", field]
    if input_data:
        cmd = ["gh", "api", "--method", method, "-H", "Content-Type: application/json",
               endpoint, "--input", "-"]

    proc = subprocess.run(
        cmd,
        capture_output=True, text=True,
        input=input_data if input_data else None,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        print(f"❌ gh api 失败 ({method} {endpoint}):", file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        sys.exit(1)
    out = proc.stdout.strip()
    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        return out


def create_blob(file_path: str) -> str:
    """上传文件内容为 blob，返回 sha"""
    full_path = REPO_ROOT / file_path
    content = full_path.read_bytes()
    content_b64 = base64.b64encode(content).decode("ascii")

    payload = json.dumps({"content": content_b64, "encoding": "base64"})
    result = gh_api("POST", f"repos/{REPO}/git/blobs", input_data=payload)
    sha = result.get("sha")
    print(f"  ✅ blob: {file_path} → {sha[:8]}")
    return sha


def main():
    print(f"=== 通过 GitHub API 推送 {len(FILES)} 个文件到 {BRANCH} ===\n")

    # 1. 获取 master 当前 commit 的 sha 和 tree sha
    print("[1/5] 获取当前 master HEAD...")
    ref = gh_api("GET", f"repos/{REPO}/git/refs/heads/{BRANCH}")
    parent_sha = ref["object"]["sha"]
    print(f"  当前 HEAD: {parent_sha[:8]}")

    parent_commit = gh_api("GET", f"repos/{REPO}/git/commits/{parent_sha}")
    base_tree_sha = parent_commit["tree"]["sha"]
    print(f"  base tree: {base_tree_sha[:8]}")

    # 2. 为每个文件创建 blob
    print("\n[2/5] 创建 blobs...")
    tree_items = []
    for fp in FILES:
        blob_sha = create_blob(fp)
        tree_items.append({
            "path": fp,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha,
        })

    # 3. 创建新 tree（基于 base tree，覆盖/新增指定文件）
    print("\n[3/5] 创建新 tree...")
    tree_payload = json.dumps({"base_tree": base_tree_sha, "tree": tree_items})
    new_tree = gh_api("POST", f"repos/{REPO}/git/trees", input_data=tree_payload)
    new_tree_sha = new_tree["sha"]
    print(f"  新 tree: {new_tree_sha[:8]}")

    # 4. 创建 commit
    print("\n[4/5] 创建 commit...")
    commit_msg = """ci: 修复部署管道 - deploy.yml 加部署开关+Node24兼容，增强 render.yaml

## deploy.yml 修复
- 去掉后端 curl 的 || true（原 bug 导致 hook URL 错也假成功）
- 加 DEPLOYMENT_ENABLED variable 开关（未配 secret 时只跑 Build Test，不假失败）
- 加 FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true（应对 Node20 弃用）
- 加 HTTP 响应码校验（非 2xx 时报警告）

## render.yaml 增强
- 加 region: singapore + healthCheckPath + buildCommand 含 init_db.py

## 文档
- 新增 docs/部署配置清单.md（5分钟配置指南）"""

    commit_payload = json.dumps({
        "message": commit_msg,
        "tree": new_tree_sha,
        "parents": [parent_sha],
    })
    new_commit = gh_api("POST", f"repos/{REPO}/git/commits", input_data=commit_payload)
    new_commit_sha = new_commit["sha"]
    print(f"  新 commit: {new_commit_sha[:8]}")

    # 5. 更新 master ref 指向新 commit
    print("\n[5/5] 更新 master 分支指向新 commit...")
    ref_payload = json.dumps({"sha": new_commit_sha, "force": False})
    gh_api("PATCH", f"repos/{REPO}/git/refs/heads/{BRANCH}", input_data=ref_payload)
    print(f"  ✅ master 已更新到 {new_commit_sha[:8]}")

    print(f"\n🎉 推送成功！commit: {new_commit_sha}")
    print(f"   https://github.com/{REPO}/commit/{new_commit_sha}")

    # 同步本地 git 到远程（让本地 ref 指向新 commit）
    print("\n[同步] 更新本地 ref...")
    subprocess.run(["git", "update-ref", f"refs/heads/{BRANCH}", new_commit_sha], cwd=str(REPO_ROOT))
    subprocess.run(["git", "update-ref", f"refs/remotes/origin/{BRANCH}", new_commit_sha], cwd=str(REPO_ROOT))
    print("  ✅ 本地已同步")


if __name__ == "__main__":
    main()
