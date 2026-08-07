#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub 仓库创建与文件上传脚本
用法: python upload_to_github.py <PAT>
"""
import sys
import os
import base64
import json
import urllib.request
import urllib.error
from urllib.parse import quote

REPO_NAME = "xianzheng-jishou-config"
REPO_DESC = "先正电子寄售取数 - 配置化工具包 | 寄售点/集团分组/开票规则/二维码读入 全配置驱动，自动生成建表取数SQL"
LOCAL_DIR = r"C:\Users\13924\Desktop\xianzheng-jishou-config"
BRANCH = "main"


def api_request(url, token, method="GET", data=None):
    """发送 GitHub API 请求"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        try:
            error_json = json.loads(error_body)
        except:
            error_json = {"message": error_body}
        return e.code, error_json


def create_repo(token):
    """创建仓库"""
    # 先检查仓库是否已存在
    url = f"https://api.github.com/repos/ygs55168/{REPO_NAME}"
    status, resp = api_request(url, token, "GET")
    if status == 200:
        print(f"ℹ️  仓库已存在: {resp['html_url']}")
        return True

    # 不存在则创建
    url = "https://api.github.com/user/repos"
    data = {
        "name": REPO_NAME,
        "description": REPO_DESC,
        "private": False,
        "auto_init": False,
        "has_issues": True,
        "has_wiki": True,
    }
    status, resp = api_request(url, token, "POST", data)
    if status == 201:
        print(f"✅ 仓库创建成功: {resp['html_url']}")
        return True
    else:
        print(f"❌ 创建仓库失败: {status} - {resp.get('message', '未知错误')}")
        return False


def get_file_sha(token, path):
    """获取文件的 SHA（用于判断是否已存在）"""
    encoded_path = quote(path)
    url = f"https://api.github.com/repos/ygs55168/{REPO_NAME}/contents/{encoded_path}?ref={BRANCH}"
    status, resp = api_request(url, token, "GET")
    if status == 200:
        return resp.get("sha")
    return None


def upload_file(token, local_path, remote_path, commit_msg):
    """上传单个文件"""
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    encoded_path = quote(remote_path)
    url = f"https://api.github.com/repos/ygs55168/{REPO_NAME}/contents/{encoded_path}"
    data = {
        "message": commit_msg,
        "content": content,
        "branch": BRANCH,
    }

    # 检查文件是否已存在
    sha = get_file_sha(token, remote_path)
    if sha:
        data["sha"] = sha
        action = "更新"
    else:
        action = "新增"

    status, resp = api_request(url, token, "PUT", data)
    if status in (200, 201):
        print(f"  ✅ {action}: {remote_path}")
        return True
    else:
        print(f"  ❌ 失败: {remote_path} - {status} - {resp.get('message', '未知错误')}")
        return False


def main():
    if len(sys.argv) < 2:
        print("用法: python upload_to_github.py <GitHub PAT>")
        sys.exit(1)

    token = sys.argv[1].strip()

    print("=" * 60)
    print("  GitHub 仓库上传工具")
    print("=" * 60)

    # 1. 创建仓库
    print("\n📦 步骤1: 创建仓库...")
    if not create_repo(token):
        sys.exit(1)

    # 2. 收集所有文件
    print(f"\n📂 步骤2: 收集文件 (本地目录: {LOCAL_DIR})")
    files = []
    for root, dirs, filenames in os.walk(LOCAL_DIR):
        # 跳过 .git 目录
        if ".git" in dirs:
            dirs.remove(".git")
        for fname in filenames:
            local_path = os.path.join(root, fname)
            rel_path = os.path.relpath(local_path, LOCAL_DIR).replace("\\", "/")
            files.append((local_path, rel_path))

    print(f"  共找到 {len(files)} 个文件")

    # 3. 上传文件
    print(f"\n🚀 步骤3: 上传文件到 GitHub...")
    success = 0
    fail = 0

    for local_path, remote_path in files:
        if upload_file(token, local_path, remote_path, f"feat: 初始化项目 - {remote_path}"):
            success += 1
        else:
            fail += 1

    # 4. 总结
    print(f"\n{'=' * 60}")
    print(f"  上传完成!")
    print(f"  ✅ 成功: {success} 个")
    print(f"  ❌ 失败: {fail} 个")
    print(f"  🌐 仓库地址: https://github.com/ygs55168/{REPO_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
