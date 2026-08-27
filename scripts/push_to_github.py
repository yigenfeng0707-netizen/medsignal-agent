"""
通过 GitHub Git Data API 批量推送代码（绕过 git push 网络问题）

流程：收集文件 → 批量创建 blob → 创建 tree → 创建 commit → 更新 main 分支 ref
适用于 git push 因网络无法连接 github.com，但 api.github.com 可达的场景。
"""

import base64
import os
import sys
import time
from pathlib import Path

import requests

# ==================== 配置 ====================
REPO_OWNER = "yigenfeng0707-netizen"
REPO_NAME = "yibao-eeg"
API_BASE = "https://api.github.com"
BRANCH = "main"
COMMIT_MSG = """feat: 医保智脑 v2.1.0 — BCI×医保创新版

基于可信数据空间的个人医保智能体，6 个专业智能体协作 + EEG 脑电健康模块。

核心能力：
- 权益管家/报销助手/健康卫士/政策参谋/安全守门/脑电卫士 6 个智能体
- BCI×医保创新全链路：EEG 采集 → 频域分析 → 健康评估 → 医保政策自动联动
- 脑电健康第 6 维：4 通道/256Hz/五频段 → 压力/注意力/睡眠/认知负荷/情绪
- 多智能体协作 + 主动式健康预警 + 可信数据空间 + 全链路可解释性

测试：92 项单元测试 + 60 项端到端冒烟测试，全部通过"""

# 从 gh CLI 获取 token
TOKEN = os.popen("gh auth token").read().strip() if not os.environ.get("GH_TOKEN") else os.environ["GH_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "yibao-eeg-push-script",
}

# ==================== 排除规则（与 .gitignore 一致）====================
EXCLUDE_DIRS = {
    ".git", "__pycache__", ".pytest_cache", "node_modules", ".next",
    "venv", "env", ".venv", "build", "dist", ".vscode", ".idea",
    "data/chroma", "data/embeddings",
}
EXCLUDE_FILES = {".env", ".env.local", "yibao.db", "yibao.db-journal",
                 "next-env.d.ts", "tsconfig.tsbuildinfo", ".DS_Store"}
EXCLUDE_EXTS = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe",
                ".db", ".sqlite", ".sqlite3", ".log", ".tmp", ".bak"}


def should_exclude(path: Path, root: Path) -> bool:
    """判断文件是否应被排除（与 .gitignore 规则一致）"""
    rel = path.relative_to(root)
    parts = rel.parts

    # 排除目录
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.endswith(".egg-info"):
            return True

    # 排除文件名
    if path.name in EXCLUDE_FILES:
        return True

    # 排除扩展名
    if path.suffix in EXCLUDE_EXTS:
        return True

    # 排除 .env 系列
    if path.name.startswith(".env") and path.name != ".env.example":
        return True

    return False


def collect_files(root: Path) -> list[tuple[str, bytes]]:
    """收集所有要推送的文件，返回 [(相对路径, 内容字节), ...]"""
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if should_exclude(path, root):
            continue
        rel = path.relative_to(root).as_posix()  # 用正斜杠（git 风格）
        try:
            content = path.read_bytes()
            files.append((rel, content))
        except Exception as e:
            print(f"  ⚠️ 跳过 {rel}: {e}")
    return files


def create_blob(content: bytes, session: requests.Session) -> str:
    """创建 git blob，返回 sha"""
    b64 = base64.b64encode(content).decode("ascii")
    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs",
        headers=HEADERS,
        json={"content": b64, "encoding": "base64"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["sha"]


def create_tree(tree_items: list[dict], session: requests.Session) -> str:
    """创建 git tree，返回 sha"""
    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/trees",
        headers=HEADERS,
        json={"tree": tree_items},
        timeout=120,
    )
    if not resp.ok:
        print(f"  ❌ Tree 创建失败: {resp.status_code}")
        print(f"  响应: {resp.text[:2000]}")
        resp.raise_for_status()
    return resp.json()["sha"]


def create_commit(tree_sha: str, parents: list[str], session: requests.Session) -> str:
    """创建 git commit，返回 sha"""
    resp = session.post(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/commits",
        headers=HEADERS,
        json={"message": COMMIT_MSG, "tree": tree_sha, "parents": parents},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["sha"]


def update_ref(sha: str, session: requests.Session) -> dict:
    """更新 main 分支 ref 指向新 commit"""
    resp = session.patch(
        f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
        headers=HEADERS,
        json={"sha": sha, "force": False},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    root = Path(__file__).resolve().parent.parent  # yibao-eeg 根目录
    print(f"📦 项目根目录: {root}")

    # 1. 收集文件
    print("📋 收集文件...")
    files = collect_files(root)
    print(f"  ✅ 共 {len(files)} 个文件待推送")

    if not files:
        print("❌ 没有文件可推送")
        sys.exit(1)

    session = requests.Session()

    # 2. 批量创建 blob（带重试）
    print("📤 创建 git blobs...")
    tree_items = []
    failed = []
    for i, (rel, content) in enumerate(files, 1):
        retry = 0
        while retry < 3:
            try:
                sha = create_blob(content, session)
                tree_items.append({
                    "path": rel,
                    "mode": "100644",
                    "type": "blob",
                    "sha": sha,
                })
                if i % 20 == 0 or i == len(files):
                    print(f"  [{i}/{len(files)}] {rel}")
                break
            except Exception as e:
                retry += 1
                if retry >= 3:
                    print(f"  ❌ 失败 {rel}: {e}")
                    failed.append(rel)
                else:
                    time.sleep(2)
    print(f"  ✅ 成功 {len(tree_items)} 个，失败 {len(failed)} 个")
    if failed:
        print(f"  失败文件: {failed}")

    if not tree_items:
        print("❌ 没有 blob 创建成功")
        sys.exit(1)

    # 3. 创建 tree
    print("🌳 创建 git tree...")
    # GitHub API 单次 tree 最多 500 个 item，分批处理
    if len(tree_items) > 500:
        print(f"  ⚠️ 文件数 {len(tree_items)} > 500，需分批创建 tree")
        # 简化：取前 500 个（本项目 134 个文件，不会触发）
        tree_items = tree_items[:500]
    tree_sha = create_tree(tree_items, session)
    print(f"  ✅ Tree SHA: {tree_sha}")

    # 4. 创建 commit（以 README 初始化 commit 作为 parent）
    print("📝 创建 git commit...")
    # 获取当前 main 分支的 commit sha 作为 parent
    try:
        ref_resp = session.get(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}",
            headers=HEADERS, timeout=30,
        )
        ref_resp.raise_for_status()
        parent_sha = ref_resp.json()["object"]["sha"]
        parents = [parent_sha]
        print(f"  ✅ Parent commit: {parent_sha}")
    except Exception as e:
        print(f"  ⚠️ 获取 parent 失败（可能是空仓库）: {e}")
        parents = []
    commit_sha = create_commit(tree_sha, parents, session)
    print(f"  ✅ Commit SHA: {commit_sha}")

    # 5. 更新 main 分支 ref
    print(f"🔄 更新 {BRANCH} 分支...")
    try:
        result = update_ref(commit_sha, session)
        print(f"  ✅ Ref 更新成功: {result.get('ref')}")
    except requests.HTTPError as e:
        # 空仓库可能需要先创建 ref
        print(f"  ⚠️ 更新 ref 失败: {e}")
        print("  尝试创建 ref...")
        resp = session.post(
            f"{API_BASE}/repos/{REPO_OWNER}/{REPO_NAME}/git/refs",
            headers=HEADERS,
            json={"ref": f"refs/heads/{BRANCH}", "sha": commit_sha},
            timeout=60,
        )
        if resp.status_code in (200, 201):
            print(f"  ✅ Ref 创建成功")
        else:
            print(f"  ❌ Ref 创建失败: {resp.status_code} {resp.text}")
            sys.exit(1)

    print(f"\n🎉 推送完成！")
    print(f"   仓库: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    print(f"   Commit: {commit_sha}")
    print(f"   文件数: {len(tree_items)}")


if __name__ == "__main__":
    main()
