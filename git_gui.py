"""
PyGit GUI - 基于 Python 的图形化 Git 客户端
功能涵盖: init, clone, add, commit, status, log, branch, checkout, merge, pull, push, diff, stash, tag, remote 等核心操作
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog, scrolledtext
import subprocess
import os
import threading
import sys
import datetime


# ─── Git 命令封装层 ───────────────────────────────────────────────────────────

class GitRunner:
    """封装 Git CLI 调用，所有 git 操作通过本层执行"""

    def __init__(self, repo_path=None):
        self.repo_path = repo_path or ""
        self.git_exe = self._find_git()

    def _find_git(self):
        """查找 git 可执行文件：优先使用内置 MinGit，其次系统 PATH"""
        # 打包为 EXE 时，PyInstaller 将 bundled_git 解压到 _MEIPASS
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
            bundled = os.path.join(base, "bundled_git", "cmd", "git.exe")
            if os.path.isfile(bundled):
                return bundled
            # 兼容其他目录结构
            bundled2 = os.path.join(base, "bundled_git", "mingw64", "bin", "git.exe")
            if os.path.isfile(bundled2):
                return bundled2

        # 非打包环境：查找项目目录下的 bundled_git
        script_dir = os.path.dirname(os.path.abspath(__file__))
        local_git = os.path.join(script_dir, "bundled_git", "cmd", "git.exe")
        if os.path.isfile(local_git):
            return local_git

        # 回退到系统 PATH 中的 git
        return "git"

    def set_repo(self, path):
        self.repo_path = path

    def run(self, args, timeout=30):
        """执行 git 命令，返回 (success, stdout, stderr)"""
        cmd = [self.git_exe] + args
        # 构建环境变量：确保内置 MinGit 的 DLL 可被找到
        env = os.environ.copy()
        if getattr(sys, 'frozen', False):
            bundled_dir = os.path.join(sys._MEIPASS, "bundled_git")
            if os.path.isdir(bundled_dir):
                mingw_bin = os.path.join(bundled_dir, "mingw64", "bin")
                usr_bin = os.path.join(bundled_dir, "usr", "bin")
                env["PATH"] = f"{mingw_bin};{usr_bin};" + env.get("PATH", "")
        try:
            result = subprocess.run(
                cmd, cwd=self.repo_path or None,
                capture_output=True, text=True,
                timeout=timeout, encoding="utf-8", errors="replace",
                env=env
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "命令执行超时"
        except FileNotFoundError:
            return False, "", "未找到 git 命令，请确认已安装 Git 并已加入 PATH"
        except Exception as e:
            return False, "", str(e)


# ─── 自定义对话框 ─────────────────────────────────────────────────────────────

class InputDialog(tk.Toplevel):
    """通用输入对话框"""

    def __init__(self, parent, title, prompt, default="", password=False):
        super().__init__(parent)
        self.title(title)
        self.geometry("420x160")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        ttk.Label(self, text=prompt, wraplength=380).pack(padx=15, pady=(15, 5))
        self.var = tk.StringVar(value=default)
        show = "*" if password else ""
        ttk.Entry(self, textvariable=self.var, width=50, show=show).pack(padx=15, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=5)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_window(self)

    def _ok(self):
        self.result = self.var.get()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


class ConfirmDialog(tk.Toplevel):
    """确认对话框"""

    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x150")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = False

        ttk.Label(self, text=message, wraplength=360, justify=tk.LEFT).pack(padx=15, pady=(15, 10))

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self._yes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._no).pack(side=tk.LEFT, padx=5)

        self.bind("<Return>", lambda e: self._yes())
        self.bind("<Escape>", lambda e: self._no())
        self.wait_window(self)

    def _yes(self):
        self.result = True
        self.destroy()

    def _no(self):
        self.result = False
        self.destroy()


# ─── 主窗口 ───────────────────────────────────────────────────────────────────

class PyGitGUI(tk.Tk):
    """PyGit 图形化 Git 客户端主窗口"""

    def __init__(self):
        super().__init__()
        self.title("PyGit - 图形化 Git 客户端")
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.git = GitRunner()
        self._setup_styles()
        self._build_menu()
        self._build_ui()
        self._update_status("就绪 — 请打开或初始化一个 Git 仓库")
        self._set_icon()

    # ── 样式 ──
    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 9))
        style.configure("TButton", font=("Microsoft YaHei UI", 9))
        style.configure("Treeview", font=("Consolas", 9), rowheight=24)
        style.configure("Treeview.Heading", font=("Microsoft YaHei UI", 9, "bold"))

    # ── 图标 ──
    def _set_icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), "pygit_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

    # ── 菜单栏 ──
    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # 文件
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开仓库...", command=self._open_repo, accelerator="Ctrl+O")
        file_menu.add_command(label="初始化仓库...", command=self._init_repo)
        file_menu.add_command(label="克隆仓库...", command=self._clone_repo)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        # 操作
        ops_menu = tk.Menu(menubar, tearoff=0)
        ops_menu.add_command(label="提交 (Commit)", command=self._do_commit, accelerator="Ctrl+S")
        ops_menu.add_command(label="拉取 (Pull)", command=self._do_pull)
        ops_menu.add_command(label="推送 (Push)", command=self._do_push)
        ops_menu.add_separator()
        ops_menu.add_command(label="暂存 (Stash)", command=self._do_stash)
        ops_menu.add_command(label="弹出暂存 (Stash Pop)", command=self._do_stash_pop)
        menubar.add_cascade(label="操作", menu=ops_menu)

        # 分支
        branch_menu = tk.Menu(menubar, tearoff=0)
        branch_menu.add_command(label="新建分支...", command=self._create_branch)
        branch_menu.add_command(label="切换分支...", command=self._checkout_branch)
        branch_menu.add_command(label="合并分支...", command=self._merge_branch)
        branch_menu.add_command(label="删除分支...", command=self._delete_branch)
        menubar.add_cascade(label="分支", menu=branch_menu)

        # 标签
        tag_menu = tk.Menu(menubar, tearoff=0)
        tag_menu.add_command(label="新建标签...", command=self._create_tag)
        tag_menu.add_command(label="删除标签...", command=self._delete_tag)
        menubar.add_cascade(label="标签", menu=tag_menu)

        # 远程
        remote_menu = tk.Menu(menubar, tearoff=0)
        remote_menu.add_command(label="添加远程仓库...", command=self._add_remote)
        remote_menu.add_command(label="查看远程仓库", command=self._show_remotes)
        remote_menu.add_command(label="拉取远程 (Fetch)", command=self._do_fetch)
        menubar.add_cascade(label="远程", menu=remote_menu)

        # 查看
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="差异对比 (Diff)", command=self._do_diff, accelerator="Ctrl+D")
        view_menu.add_command(label="完整日志", command=self._show_full_log)
        view_menu.add_command(label="仓库信息", command=self._show_repo_info)
        menubar.add_cascade(label="查看", menu=view_menu)

        # 帮助
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用教程", command=self._show_tutorial)
        help_menu.add_command(label="关于 PyGit", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        # 快捷键
        self.bind("<Control-o>", lambda e: self._open_repo())
        self.bind("<Control-s>", lambda e: self._do_commit())
        self.bind("<Control-d>", lambda e: self._do_diff())

    # ── 主界面 ──
    def _build_ui(self):
        # 顶部工具栏
        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, padx=8, pady=(8, 0))

        self.repo_label = ttk.Label(toolbar, text="未打开仓库", style="Header.TLabel")
        self.repo_label.pack(side=tk.LEFT)

        btn_right = ttk.Frame(toolbar)
        btn_right.pack(side=tk.RIGHT)

        ttk.Button(btn_right, text="刷新", command=self._refresh_all, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_right, text="提交", command=self._do_commit, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_right, text="拉取", command=self._do_pull, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_right, text="推送", command=self._do_push, width=8).pack(side=tk.LEFT, padx=2)

        # 分支信息
        self.branch_label = ttk.Label(toolbar, text="", foreground="#2266aa")
        self.branch_label.pack(side=tk.LEFT, padx=20)

        # 主体 Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: 文件状态
        self._build_status_tab()
        # Tab 2: 提交历史
        self._build_log_tab()
        # Tab 3: 分支管理
        self._build_branch_tab()
        # Tab 4: 输出终端
        self._build_terminal_tab()

        # 底部状态栏
        status_bar = ttk.Frame(self)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(status_bar, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT, padx=10, pady=3)
        self.progress = ttk.Progressbar(status_bar, mode="indeterminate", length=120)
        self.progress.pack(side=tk.RIGHT, padx=10, pady=3)

    # ── Tab 1: 文件状态 ──
    def _build_status_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" 文件状态 ")

        # 暂存区
        staged_frame = ttk.LabelFrame(frame, text="已暂存 (Staged)", padding=5)
        staged_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        self.staged_tree = ttk.Treeview(staged_frame, columns=("status", "path"), show="headings", selectmode="extended")
        self.staged_tree.heading("status", text="状态")
        self.staged_tree.heading("path", text="文件路径")
        self.staged_tree.column("status", width=60, anchor=tk.CENTER)
        self.staged_tree.column("path", width=600)
        staged_scroll = ttk.Scrollbar(staged_frame, orient=tk.VERTICAL, command=self.staged_tree.yview)
        self.staged_tree.configure(yscrollcommand=staged_scroll.set)
        staged_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.staged_tree.pack(fill=tk.BOTH, expand=True)

        # 右键菜单 - 暂存区
        staged_ctx = tk.Menu(self.staged_tree, tearoff=0)
        staged_ctx.add_command(label="取消暂存 (Unstage)", command=self._unstage_selected)
        staged_ctx.add_command(label="查看差异 (Diff)", command=lambda: self._diff_tree(self.staged_tree))
        self.staged_tree.bind("<Button-3>", lambda e: self._show_ctx(e, staged_ctx))

        # 操作按钮行
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=5, pady=3)
        ttk.Button(btn_row, text="全部暂存 (Add All)", command=self._stage_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="暂存选中", command=self._stage_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="取消暂存选中", command=self._unstage_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="刷新", command=self._refresh_status).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_row, text="丢弃选中更改", command=self._discard_selected).pack(side=tk.LEFT, padx=3)

        # 未暂存区
        unstaged_frame = ttk.LabelFrame(frame, text="未暂存 (Unstaged)", padding=5)
        unstaged_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))

        self.unstaged_tree = ttk.Treeview(unstaged_frame, columns=("status", "path"), show="headings", selectmode="extended")
        self.unstaged_tree.heading("status", text="状态")
        self.unstaged_tree.heading("path", text="文件路径")
        self.unstaged_tree.column("status", width=60, anchor=tk.CENTER)
        self.unstaged_tree.column("path", width=600)
        unstaged_scroll = ttk.Scrollbar(unstaged_frame, orient=tk.VERTICAL, command=self.unstaged_tree.yview)
        self.unstaged_tree.configure(yscrollcommand=unstaged_scroll.set)
        unstaged_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.unstaged_tree.pack(fill=tk.BOTH, expand=True)

        # 右键菜单 - 未暂存区
        unstaged_ctx = tk.Menu(self.unstaged_tree, tearoff=0)
        unstaged_ctx.add_command(label="暂存 (Stage)", command=self._stage_selected)
        unstaged_ctx.add_command(label="查看差异 (Diff)", command=lambda: self._diff_tree(self.unstaged_tree))
        unstaged_ctx.add_command(label="丢弃更改 (Discard)", command=self._discard_selected)
        self.unstaged_tree.bind("<Button-3>", lambda e: self._show_ctx(e, unstaged_ctx))

        # 双击查看差异
        self.staged_tree.bind("<Double-1>", lambda e: self._diff_tree(self.staged_tree))
        self.unstaged_tree.bind("<Double-1>", lambda e: self._diff_tree(self.unstaged_tree))

    # ── Tab 2: 提交历史 ──
    def _build_log_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" 提交历史 ")

        # 搜索栏
        search_frame = ttk.Frame(frame)
        search_frame.pack(fill=tk.X, padx=5, pady=(5, 2))
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=3)
        self.log_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.log_search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=3)
        ttk.Button(search_frame, text="搜索", command=self._search_log).pack(side=tk.LEFT, padx=3)
        ttk.Button(search_frame, text="重置", command=self._refresh_log).pack(side=tk.LEFT, padx=3)

        # 日志列表
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        self.log_tree = ttk.Treeview(log_frame, columns=("hash", "date", "author", "message"), show="headings", selectmode="browse")
        self.log_tree.heading("hash", text="SHA")
        self.log_tree.heading("date", text="日期")
        self.log_tree.heading("author", text="作者")
        self.log_tree.heading("message", text="提交信息")
        self.log_tree.column("hash", width=80)
        self.log_tree.column("date", width=140)
        self.log_tree.column("author", width=140)
        self.log_tree.column("message", width=500)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_tree.pack(fill=tk.BOTH, expand=True)

        # 右键菜单
        log_ctx = tk.Menu(self.log_tree, tearoff=0)
        log_ctx.add_command(label="查看差异 (Diff)", command=self._diff_commit)
        log_ctx.add_command(label="查看此提交的变更文件", command=self._show_commit_files)
        log_ctx.add_command(label="回退到此提交 (Soft Reset)", command=self._reset_soft)
        log_ctx.add_command(label="复制 SHA", command=self._copy_sha)
        log_ctx.add_command(label="创建分支于此", command=self._branch_at_commit)
        log_ctx.add_command(label="创建标签于此", command=self._tag_at_commit)
        log_ctx.add_command(label="变基到此提交 (Revert)", command=self._revert_commit)
        self.log_tree.bind("<Button-3>", lambda e: self._show_ctx(e, log_ctx))
        self.log_tree.bind("<Double-1>", lambda e: self._show_commit_files())

        # 详情区
        detail_frame = ttk.LabelFrame(frame, text="提交详情", padding=5)
        detail_frame.pack(fill=tk.X, padx=5, pady=(2, 5))
        self.log_detail = scrolledtext.ScrolledText(detail_frame, height=5, font=("Consolas", 9), state=tk.DISABLED)
        self.log_detail.pack(fill=tk.X)
        self.log_tree.bind("<<TreeviewSelect>>", self._on_log_select)

    # ── Tab 3: 分支管理 ──
    def _build_branch_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" 分支管理 ")

        # 按钮行
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_row, text="新建分支", command=self._create_branch).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="切换分支", command=self._checkout_branch).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="合并分支", command=self._merge_branch).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="删除分支", command=self._delete_branch).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_row, text="刷新", command=self._refresh_branches).pack(side=tk.RIGHT, padx=3)

        # 分支列表
        self.branch_tree = ttk.Treeview(frame, columns=("name", "current", "upstream"), show="headings", selectmode="browse")
        self.branch_tree.heading("name", text="分支名称")
        self.branch_tree.heading("current", text="当前")
        self.branch_tree.heading("upstream", text="上游跟踪")
        self.branch_tree.column("name", width=300)
        self.branch_tree.column("current", width=80, anchor=tk.CENTER)
        self.branch_tree.column("upstream", width=300)
        branch_scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.branch_tree.yview)
        self.branch_tree.configure(yscrollcommand=branch_scroll.set)
        branch_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.branch_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 标签区
        tag_label_frame = ttk.LabelFrame(frame, text="标签 (Tags)", padding=5)
        tag_label_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.tag_list = ttk.Treeview(tag_label_frame, columns=("name", "sha", "message"), show="headings", selectmode="browse")
        self.tag_list.heading("name", text="标签名")
        self.tag_list.heading("sha", text="SHA")
        self.tag_list.heading("message", text="信息")
        self.tag_list.column("name", width=200)
        self.tag_list.column("sha", width=100)
        self.tag_list.column("message", width=400)
        tag_scroll = ttk.Scrollbar(tag_label_frame, orient=tk.VERTICAL, command=self.tag_list.yview)
        self.tag_list.configure(yscrollcommand=tag_scroll.set)
        tag_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tag_list.pack(fill=tk.X)

    # ── Tab 4: 终端输出 ──
    def _build_terminal_tab(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=" 终端输出 ")

        self.terminal = scrolledtext.ScrolledText(frame, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4",
                                                   insertbackground="white", state=tk.DISABLED, wrap=tk.WORD)
        self.terminal.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.terminal.tag_configure("cmd", foreground="#569cd6", font=("Consolas", 10, "bold"))
        self.terminal.tag_configure("ok", foreground="#6a9955")
        self.terminal.tag_configure("err", foreground="#f44747")
        self.terminal.tag_configure("info", foreground="#dcdcaa")

        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Button(btn_row, text="清屏", command=self._clear_terminal).pack(side=tk.RIGHT, padx=3)

        # 自定义命令输入
        cmd_frame = ttk.Frame(frame)
        cmd_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        ttk.Label(cmd_frame, text="git").pack(side=tk.LEFT, padx=3)
        self.cmd_var = tk.StringVar()
        cmd_entry = ttk.Entry(cmd_frame, textvariable=self.cmd_var, width=60)
        cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        cmd_entry.bind("<Return>", lambda e: self._run_custom_cmd())
        ttk.Button(cmd_frame, text="执行", command=self._run_custom_cmd).pack(side=tk.LEFT, padx=3)

    # ── 异步执行 ──
    def _run_async(self, func, callback=None):
        """在后台线程执行耗时操作"""
        self.progress.start(10)

        def wrapper():
            try:
                result = func()
                self.after(0, lambda: self._on_async_done(result, callback))
            except Exception as e:
                self.after(0, lambda: self._on_async_done((False, "", str(e)), callback))

        t = threading.Thread(target=wrapper, daemon=True)
        t.start()

    def _on_async_done(self, result, callback):
        self.progress.stop()
        if callback:
            callback(result)

    def _git_run(self, args, callback=None, show_in_terminal=True):
        """执行 git 命令并可选地显示在终端"""
        if show_in_terminal:
            self._log_terminal(f"$ git {' '.join(args)}", "cmd")

        def do_run():
            return self.git.run(args)

        def on_done(result):
            ok, out, err = result
            if show_in_terminal:
                if out.strip():
                    self._log_terminal(out.strip(), "ok" if ok else "info")
                if err.strip():
                    self._log_terminal(err.strip(), "err" if not ok else "info")
            if callback:
                callback(ok, out, err)

        self._run_async(do_run, on_done)

    # ── 终端日志 ──
    def _log_terminal(self, text, tag="info"):
        self.terminal.configure(state=tk.NORMAL)
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.terminal.insert(tk.END, f"[{timestamp}] {text}\n", tag)
        self.terminal.see(tk.END)
        self.terminal.configure(state=tk.DISABLED)

    def _clear_terminal(self):
        self.terminal.configure(state=tk.NORMAL)
        self.terminal.delete("1.0", tk.END)
        self.terminal.configure(state=tk.DISABLED)

    # ── 右键菜单 ──
    def _show_ctx(self, event, menu):
        tree = event.widget
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            menu.post(event.x_root, event.y_root)

    # ── 状态栏 ──
    def _update_status(self, text):
        self.status_var.set(text)

    # ═══════════════════════════════════════════════════════════════════════════
    # 仓库操作
    # ═══════════════════════════════════════════════════════════════════════════

    def _open_repo(self):
        path = filedialog.askdirectory(title="选择 Git 仓库目录")
        if not path:
            return
        # 验证是否是 git 仓库
        self.git.set_repo(path)
        ok, out, err = self.git.run(["rev-parse", "--is-inside-work-tree"])
        if ok and "true" in out:
            self._on_repo_loaded(path)
        else:
            self.git.set_repo("")
            messagebox.showerror("错误", f"所选目录不是 Git 仓库:\n{err}", parent=self)

    def _on_repo_loaded(self, path):
        self.repo_label.config(text=f"📁 {os.path.basename(path)}")
        self._update_status(f"已打开: {path}")
        self._log_terminal(f"已打开仓库: {path}", "ok")
        self._refresh_all()

    def _init_repo(self):
        path = filedialog.askdirectory(title="选择要初始化为 Git 仓库的目录")
        if not path:
            return
        self.git.set_repo(path)
        ok, out, err = self.git.run(["init"])
        if ok:
            self._on_repo_loaded(path)
            messagebox.showinfo("成功", f"已在以下目录初始化 Git 仓库:\n{path}", parent=self)
        else:
            messagebox.showerror("错误", f"初始化失败:\n{err}", parent=self)

    def _clone_repo(self):
        url = simpledialog.askstring("克隆仓库", "请输入远程仓库 URL:", parent=self)
        if not url:
            return
        path = filedialog.askdirectory(title="选择克隆目标目录（父目录）")
        if not path:
            return
        self._update_status("正在克隆...")
        self._log_terminal(f"$ git clone {url}", "cmd")

        def do_clone():
            env = os.environ.copy()
            if getattr(sys, 'frozen', False):
                bundled_dir = os.path.join(sys._MEIPASS, "bundled_git")
                if os.path.isdir(bundled_dir):
                    mingw_bin = os.path.join(bundled_dir, "mingw64", "bin")
                    usr_bin = os.path.join(bundled_dir, "usr", "bin")
                    env["PATH"] = f"{mingw_bin};{usr_bin};" + env.get("PATH", "")
            result = subprocess.run(
                [self.git.git_exe, "clone", url],
                cwd=path, capture_output=True, text=True,
                timeout=300, encoding="utf-8", errors="replace",
                env=env
            )
            return result.returncode == 0, result.stdout, result.stderr

        def on_done(result):
            ok, out, err = result
            if out.strip():
                self._log_terminal(out.strip(), "ok" if ok else "info")
            if err.strip():
                self._log_terminal(err.strip(), "err" if not ok else "info")
            if ok:
                # 找到克隆出的子目录
                dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
                if dirs:
                    cloned = os.path.join(path, dirs[-1])
                    self.git.set_repo(cloned)
                    self._on_repo_loaded(cloned)
                messagebox.showinfo("成功", "克隆完成!", parent=self)
            else:
                messagebox.showerror("错误", f"克隆失败:\n{err}", parent=self)
                self._update_status("克隆失败")

        self._run_async(do_clone, on_done)

    # ═══════════════════════════════════════════════════════════════════════════
    # 刷新
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_all(self):
        if not self.git.repo_path:
            return
        self._refresh_status()
        self._refresh_log()
        self._refresh_branches()

    def _refresh_status(self):
        """刷新文件状态（暂存区 + 未暂存区）"""
        if not self.git.repo_path:
            return

        # 清空
        for item in self.staged_tree.get_children():
            self.staged_tree.delete(item)
        for item in self.unstaged_tree.get_children():
            self.unstaged_tree.delete(item)

        ok, out, err = self.git.run(["status", "--porcelain"])
        if not ok:
            self._update_status(f"获取状态失败: {err}")
            return

        staged_count = 0
        unstaged_count = 0

        status_map = {
            "M": "修改", "A": "新增", "D": "删除", "R": "重命名",
            "C": "复制", "U": "未合并", "?": "未跟踪", "!": "忽略"
        }

        for line in out.strip().splitlines():
            if len(line) < 4:
                continue
            xy = line[:2]
            filepath = line[3:]
            x, y = xy[0], xy[1]

            # 暂存区 (X 列)
            if x != " " and x != "?":
                status_text = status_map.get(x, x)
                self.staged_tree.insert("", tk.END, values=(status_text, filepath))
                staged_count += 1

            # 未暂存区 (Y 列)
            if y != " " and y != "":
                status_text = status_map.get(y, y)
                self.unstaged_tree.insert("", tk.END, values=(status_text, filepath))
                unstaged_count += 1

        # 更新分支标签
        ok2, branch_out, _ = self.git.run(["branch", "--show-current"])
        if ok2 and branch_out.strip():
            self.branch_label.config(text=f"🌿 {branch_out.strip()}")

        self._update_status(f"已暂存 {staged_count} 个文件 | 未暂存 {unstaged_count} 个文件")

    def _refresh_log(self, search_term=""):
        """刷新提交历史"""
        if not self.git.repo_path:
            return

        for item in self.log_tree.get_children():
            self.log_tree.delete(item)

        args = ["log", "--oneline", "--format=%h|%ai|%an|%s", "-200"]
        if search_term:
            args += ["--grep", search_term, "-i"]

        ok, out, err = self.git.run(args)
        if not ok:
            return

        for line in out.strip().splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                sha, date, author, msg = parts
                date_short = date[:16] if len(date) >= 16 else date
                self.log_tree.insert("", tk.END, values=(sha, date_short, author, msg))

    def _search_log(self):
        self._refresh_log(self.log_search_var.get().strip())

    def _refresh_branches(self):
        """刷新分支和标签列表"""
        if not self.git.repo_path:
            return

        for item in self.branch_tree.get_children():
            self.branch_tree.delete(item)
        for item in self.tag_list.get_children():
            self.tag_list.delete(item)

        # 分支
        ok, out, _ = self.git.run(["branch", "-vv"])
        if ok:
            for line in out.strip().splitlines():
                current = "●" if line.startswith("*") else ""
                name = line.lstrip("* ").strip()
                # 提取上游信息
                upstream = ""
                if "[" in name and "]" in name:
                    start = name.index("[") + 1
                    end = name.index("]")
                    upstream = name[start:end]
                    name = name[:start - 1].strip()
                self.branch_tree.insert("", tk.END, values=(name, current, upstream))

        # 标签
        ok2, tags_out, _ = self.git.run(["tag", "-l", "--format=%(refname:short)|%(objectname:short)|%(subject)"])
        if ok2:
            for line in tags_out.strip().splitlines():
                parts = line.split("|", 2)
                if len(parts) == 3:
                    self.tag_list.insert("", tk.END, values=parts)
                elif parts:
                    self.tag_list.insert("", tk.END, values=(parts[0], "", ""))

    # ═══════════════════════════════════════════════════════════════════════════
    # 暂存 / 取消暂存
    # ═══════════════════════════════════════════════════════════════════════════

    def _stage_all(self):
        self._git_run(["add", "-A"], callback=lambda ok, o, e: self._refresh_status())

    def _stage_selected(self):
        items = self.unstaged_tree.selection()
        if not items:
            messagebox.showinfo("提示", "请先选择要暂存的文件", parent=self)
            return
        for item in items:
            path = self.unstaged_tree.item(item, "values")[1]
            self._git_run(["add", path], show_in_terminal=True,
                          callback=lambda ok, o, e: self._refresh_status())

    def _unstage_selected(self):
        items = self.staged_tree.selection()
        if not items:
            messagebox.showinfo("提示", "请先选择要取消暂存的文件", parent=self)
            return
        for item in items:
            path = self.staged_tree.item(item, "values")[1]
            self._git_run(["reset", "HEAD", path], show_in_terminal=True,
                          callback=lambda ok, o, e: self._refresh_status())

    def _discard_selected(self):
        items = self.unstaged_tree.selection()
        if not items:
            return
        files = [self.unstaged_tree.item(item, "values")[1] for item in items]
        dlg = ConfirmDialog(self, "确认丢弃", f"确定要丢弃以下文件的更改吗？此操作不可撤销。\n\n" + "\n".join(files))
        if not dlg.result:
            return
        for f in files:
            self._git_run(["checkout", "--", f], show_in_terminal=True,
                          callback=lambda ok, o, e: self._refresh_status())

    # ═══════════════════════════════════════════════════════════════════════════
    # 提交
    # ═══════════════════════════════════════════════════════════════════════════

    def _do_commit(self):
        if not self.git.repo_path:
            messagebox.showwarning("提示", "请先打开一个仓库", parent=self)
            return

        # 检查是否有暂存内容
        ok, out, _ = self.git.run(["diff", "--cached", "--stat"])
        if ok and not out.strip():
            # 没有暂存内容，询问是否全部暂存后提交
            dlg = ConfirmDialog(self, "无暂存内容", "当前没有已暂存的更改。\n是否暂存所有更改并提交？")
            if not dlg.result:
                return
            self.git.run(["add", "-A"])

        msg = simpledialog.askstring("提交", "请输入提交信息:", parent=self)
        if not msg:
            return
        self._git_run(["commit", "-m", msg], callback=lambda ok, o, e: self._refresh_all())

    # ═══════════════════════════════════════════════════════════════════════════
    # 拉取 / 推送
    # ═══════════════════════════════════════════════════════════════════════════

    def _do_pull(self):
        if not self.git.repo_path:
            return
        self._update_status("正在拉取...")
        self._git_run(["pull"], callback=lambda ok, o, e: (self._refresh_all(), self._update_status("拉取完成")))

    def _do_push(self):
        if not self.git.repo_path:
            return
        self._update_status("正在推送...")
        self._git_run(["push"], callback=lambda ok, o, e: self._update_status("推送完成"))

    def _do_fetch(self):
        if not self.git.repo_path:
            return
        self._update_status("正在获取...")
        self._git_run(["fetch", "--all"], callback=lambda ok, o, e: (self._refresh_branches(), self._update_status("获取完成")))

    # ═══════════════════════════════════════════════════════════════════════════
    # 暂存 (Stash)
    # ═══════════════════════════════════════════════════════════════════════════

    def _do_stash(self):
        if not self.git.repo_path:
            return
        msg = simpledialog.askstring("暂存 (Stash)", "请输入暂存信息（可选）:", parent=self) or ""
        args = ["stash", "push"]
        if msg:
            args += ["-m", msg]
        self._git_run(args, callback=lambda ok, o, e: self._refresh_status())

    def _do_stash_pop(self):
        if not self.git.repo_path:
            return
        self._git_run(["stash", "pop"], callback=lambda ok, o, e: self._refresh_status())

    # ═══════════════════════════════════════════════════════════════════════════
    # 分支操作
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_branch(self):
        if not self.git.repo_path:
            return
        name = simpledialog.askstring("新建分支", "请输入分支名称:", parent=self)
        if not name:
            return
        dlg = ConfirmDialog(self, "切换分支", f"是否切换到新分支 '{name}'？")
        if dlg.result:
            self._git_run(["checkout", "-b", name], callback=lambda ok, o, e: self._refresh_all())
        else:
            self._git_run(["branch", name], callback=lambda ok, o, e: self._refresh_branches())

    def _checkout_branch(self):
        if not self.git.repo_path:
            return
        ok, out, _ = self.git.run(["branch", "--list", "--format=%(refname:short)"])
        if not ok or not out.strip():
            return
        branches = [b.strip() for b in out.strip().splitlines() if b.strip()]

        dlg = BranchSelectDialog(self, "切换分支", "请选择要切换的分支:", branches)
        if dlg.result:
            self._git_run(["checkout", dlg.result], callback=lambda ok, o, e: self._refresh_all())

    def _merge_branch(self):
        if not self.git.repo_path:
            return
        ok, out, _ = self.git.run(["branch", "--list", "--format=%(refname:short)"])
        if not ok or not out.strip():
            return
        branches = [b.strip() for b in out.strip().splitlines() if b.strip()]
        current = ""
        ok2, cur, _ = self.git.run(["branch", "--show-current"])
        if ok2:
            current = cur.strip()
            branches = [b for b in branches if b != current]

        dlg = BranchSelectDialog(self, "合并分支", f"将以下分支合并到 '{current}':", branches)
        if dlg.result:
            self._git_run(["merge", dlg.result], callback=lambda ok, o, e: self._refresh_all())

    def _delete_branch(self):
        if not self.git.repo_path:
            return
        ok, out, _ = self.git.run(["branch", "--list", "--format=%(refname:short)"])
        if not ok or not out.strip():
            return
        branches = [b.strip() for b in out.strip().splitlines() if b.strip()]
        current = ""
        ok2, cur, _ = self.git.run(["branch", "--show-current"])
        if ok2:
            current = cur.strip()
            branches = [b for b in branches if b != current]

        dlg = BranchSelectDialog(self, "删除分支", "请选择要删除的分支:", branches)
        if dlg.result:
            self._git_run(["branch", "-d", dlg.result], callback=lambda ok, o, e: self._refresh_branches())

    # ═══════════════════════════════════════════════════════════════════════════
    # 标签操作
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_tag(self):
        if not self.git.repo_path:
            return
        name = simpledialog.askstring("新建标签", "请输入标签名称:", parent=self)
        if not name:
            return
        msg = simpledialog.askstring("标签信息", "请输入标签说明（可选）:", parent=self) or ""
        args = ["tag"]
        if msg:
            args += ["-a", name, "-m", msg]
        else:
            args.append(name)
        self._git_run(args, callback=lambda ok, o, e: self._refresh_branches())

    def _delete_tag(self):
        if not self.git.repo_path:
            return
        ok, out, _ = self.git.run(["tag", "-l"])
        if not ok or not out.strip():
            messagebox.showinfo("提示", "当前没有标签", parent=self)
            return
        tags = [t.strip() for t in out.strip().splitlines() if t.strip()]
        dlg = BranchSelectDialog(self, "删除标签", "请选择要删除的标签:", tags)
        if dlg.result:
            self._git_run(["tag", "-d", dlg.result], callback=lambda ok, o, e: self._refresh_branches())

    # ═══════════════════════════════════════════════════════════════════════════
    # 远程仓库
    # ═══════════════════════════════════════════════════════════════════════════

    def _add_remote(self):
        if not self.git.repo_path:
            return
        name = simpledialog.askstring("添加远程仓库", "请输入远程名称 (如 origin):", parent=self)
        if not name:
            return
        url = simpledialog.askstring("添加远程仓库", "请输入远程 URL:", parent=self)
        if not url:
            return
        self._git_run(["remote", "add", name, url], callback=lambda ok, o, e: self._refresh_branches())

    def _show_remotes(self):
        if not self.git.repo_path:
            return
        ok, out, err = self.git.run(["remote", "-v"])
        if ok:
            messagebox.showinfo("远程仓库", out or "(无远程仓库)", parent=self)
        else:
            messagebox.showerror("错误", err, parent=self)

    # ═══════════════════════════════════════════════════════════════════════════
    # Diff 查看
    # ═══════════════════════════════════════════════════════════════════════════

    def _diff_tree(self, tree):
        items = tree.selection()
        if not items:
            return
        for item in items:
            path = tree.item(item, "values")[1]
            # 判断是暂存还是未暂存
            if tree == self.staged_tree:
                self._git_run(["diff", "--cached", path])
            else:
                self._git_run(["diff", path])
        self.notebook.select(3)  # 切换到终端标签

    def _do_diff(self):
        if not self.git.repo_path:
            return
        self._git_run(["diff", "--stat"])
        self.notebook.select(3)

    def _diff_commit(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        self._git_run(["diff", f"{sha}~1", sha])
        self.notebook.select(3)

    def _show_commit_files(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        self._git_run(["show", "--stat", sha])
        self.notebook.select(3)

    # ═══════════════════════════════════════════════════════════════════════════
    # 日志操作
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_log_select(self, event):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        ok, out, _ = self.git.run(["show", "--format=full", "-s", sha])
        if ok:
            self.log_detail.configure(state=tk.NORMAL)
            self.log_detail.delete("1.0", tk.END)
            self.log_detail.insert("1.0", out)
            self.log_detail.configure(state=tk.DISABLED)

    def _show_full_log(self):
        if not self.git.repo_path:
            return
        self._git_run(["log", "--graph", "--oneline", "--all", "-50"])
        self.notebook.select(3)

    def _copy_sha(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        self.clipboard_clear()
        self.clipboard_append(sha)
        self._update_status(f"已复制 SHA: {sha}")

    def _reset_soft(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        dlg = ConfirmDialog(self, "确认回退", f"确定要软回退到提交 {sha} 吗？\n(工作区和暂存区的内容不会丢失)")
        if dlg.result:
            self._git_run(["reset", "--soft", sha], callback=lambda ok, o, e: self._refresh_all())

    def _branch_at_commit(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        name = simpledialog.askstring("创建分支", f"在提交 {sha} 处创建分支:", parent=self)
        if name:
            self._git_run(["branch", name, sha], callback=lambda ok, o, e: self._refresh_branches())

    def _tag_at_commit(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        name = simpledialog.askstring("创建标签", f"在提交 {sha} 处创建标签:", parent=self)
        if name:
            self._git_run(["tag", name, sha], callback=lambda ok, o, e: self._refresh_branches())

    def _revert_commit(self):
        items = self.log_tree.selection()
        if not items:
            return
        sha = self.log_tree.item(items[0], "values")[0]
        dlg = ConfirmDialog(self, "确认 Revert", f"确定要 revert 提交 {sha} 吗？\n将创建一个新提交来撤销该变更。")
        if dlg.result:
            self._git_run(["revert", "--no-edit", sha], callback=lambda ok, o, e: self._refresh_all())

    def _show_repo_info(self):
        if not self.git.repo_path:
            return
        ok, out, _ = self.git.run(["remote", "-v"])
        remote_info = out if ok else "(无)"
        ok2, head, _ = self.git.run(["rev-parse", "HEAD"])
        head_info = head.strip() if ok2 else "(无)"
        ok3, count, _ = self.git.run(["rev-list", "--count", "HEAD"])
        count_info = count.strip() if ok3 else "(无)"

        info = f"仓库路径: {self.git.repo_path}\n当前 HEAD: {head_info}\n提交总数: {count_info}\n\n远程仓库:\n{remote_info}"
        messagebox.showinfo("仓库信息", info, parent=self)

    # ═══════════════════════════════════════════════════════════════════════════
    # 自定义命令
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_custom_cmd(self):
        cmd_str = self.cmd_var.get().strip()
        if not cmd_str:
            return
        args = cmd_str.split()
        self._git_run(args, callback=lambda ok, o, e: self._refresh_all())
        self.cmd_var.set("")

    # ═══════════════════════════════════════════════════════════════════════════
    # 教程与关于
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_tutorial(self):
        tutorial_path = os.path.join(os.path.dirname(__file__), "使用教程.md")
        if os.path.exists(tutorial_path):
            with open(tutorial_path, "r", encoding="utf-8") as f:
                content = f.read()
            win = tk.Toplevel(self)
            win.title("PyGit 使用教程")
            win.geometry("750x600")
            text = scrolledtext.ScrolledText(win, font=("Microsoft YaHei UI", 10), wrap=tk.WORD, padx=15, pady=10)
            text.pack(fill=tk.BOTH, expand=True)
            text.insert("1.0", content)
            text.configure(state=tk.DISABLED)
        else:
            messagebox.showinfo("教程", "使用教程文件未找到，请查看项目目录中的 使用教程.md 文件。", parent=self)

    def _show_about(self):
        about_text = (
            "PyGit - 图形化 Git 客户端\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "版本: 1.0.0\n"
            "基于 Python + Tkinter 构建\n\n"
            "功能涵盖 Git 核心操作:\n"
            "• 仓库管理 (init / clone)\n"
            "• 文件暂存与提交\n"
            "• 分支创建、切换、合并、删除\n"
            "• 远程拉取、推送、获取\n"
            "• 提交历史查看与搜索\n"
            "• 差异对比 (Diff)\n"
            "• 暂存 (Stash) 管理\n"
            "• 标签 (Tag) 管理\n"
            "• 回退 (Reset) / 撤销 (Revert)\n"
            "• 自定义 Git 命令终端\n\n"
            "© 2026 PyGit Project"
        )
        messagebox.showinfo("关于 PyGit", about_text, parent=self)


class BranchSelectDialog(tk.Toplevel):
    """分支/标签选择对话框"""

    def __init__(self, parent, title, prompt, items):
        super().__init__(parent)
        self.title(title)
        self.geometry("380x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        ttk.Label(self, text=prompt, wraplength=340).pack(padx=15, pady=(15, 5))

        listbox_frame = ttk.Frame(self)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        self.listbox = tk.Listbox(listbox_frame, font=("Consolas", 10), selectmode=tk.SINGLE)
        scroll = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        for item in items:
            self.listbox.insert(tk.END, item)

        if items:
            self.listbox.selection_set(0)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="确定", command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._cancel).pack(side=tk.LEFT, padx=5)

        self.listbox.bind("<Double-1>", lambda e: self._ok())
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self._cancel())
        self.wait_window(self)

    def _ok(self):
        sel = self.listbox.curselection()
        if sel:
            self.result = self.listbox.get(sel[0])
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ─── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    app = PyGitGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
