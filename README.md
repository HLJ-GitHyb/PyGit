<p align="center">
  <img src="pygit_icon.png" alt="PyGit Logo" width="128"/>
</p>

<h1 align="center">PyGit - 图形化 Git 客户端</h1>

<p align="center">
  基于 Python + Tkinter 构建的全功能图形化 Git 客户端<br>
  <b>零外部依赖（除 Pillow），开箱即用</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/Git-2.0%2B-orange?logo=git" alt="Git"/>
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform"/>
</p>

---

## ✨ 功能特性

| 模块 | 支持的操作 |
|------|-----------|
| **仓库管理** | `init` 初始化 · `clone` 克隆 · 打开已有仓库 |
| **文件操作** | `add` 暂存 · `reset` 取消暂存 · `checkout` 丢弃更改 · `diff` 差异对比 |
| **提交管理** | `commit` 提交 · `log` 历史查看与搜索 · `show` 详情 · `reset --soft` 回退 · `revert` 撤销 |
| **分支管理** | `branch` 创建/删除 · `checkout` 切换 · `merge` 合并 |
| **远程操作** | `pull` 拉取 · `push` 推送 · `fetch` 获取 · `remote` 管理 |
| **暂存管理** | `stash push` 保存 · `stash pop` 恢复 |
| **标签管理** | `tag` 创建 · `tag -d` 删除 · 在指定提交处打标签 |
| **内置终端** | 自定义 Git 命令 · 彩色输出 · 命令历史 |

## 🚀 快速开始

### 下载
版本1：

百度网盘：链接: https://pan.baidu.com/s/1cQwFOIDAoXj-OU7CzblnUw?pwd=ivvw 提取码: ivvw

夸克网盘：链接：https://pan.quark.cn/s/4274c7e1da92?pwd=bMwy 提取码：bMwy

蓝奏云：链接：https://wwalq.lanzoum.com/iF3Qf4e7nsob 密码:8uej

### 📖 界面说明

界面分为四个标签页：

| 标签页 | 功能 |
|--------|------|
| **文件状态** | 查看暂存区 / 未暂存区的文件变更，支持右键菜单操作 |
| **提交历史** | 浏览最近 200 条提交，支持搜索、差异查看、回退、Revert |
| **分支管理** | 管理本地/远程分支和标签 |
| **终端输出** | 查看所有 Git 命令的彩色输出，支持输入自定义命令 |

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+O` | 打开仓库 |
| `Ctrl+S` | 提交 |
| `Ctrl+D` | 查看差异 |
```

## 🧠 Git 原理图解
```
本项目深度理解 Git 工作原理，基于三棵树模型构建：

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  工作区      │     │  暂存区      │     │  本地仓库    │
│ Working     │────▶│ Index /     │────▶│ HEAD /      │
│ Tree        │ add │ Staging     │commit│ Repository  │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                                       │
       └─────────── checkout ──────────────────┘


所有 Git 操作通过 `GitRunner` 封装层执行，保证命令安全性和超时处理。
```

## 📄 许可证

[MIT License](LICENSE) — 自由使用、修改和分发。

---

<p align="center">PyGit v1.0.0 · Made with Python + Tkinter</p>
