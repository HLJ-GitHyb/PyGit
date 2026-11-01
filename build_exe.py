"""
PyGit EXE 打包脚本
运行后在 dist/ 目录生成 PyGit.exe
"""

import subprocess
import sys
import os

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    bundled_git_dir = os.path.join(script_dir, "bundled_git")
    has_bundled_git = os.path.isdir(bundled_git_dir)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "PyGit",
        "--onefile",           # 打包为单个 EXE 文件
        "--windowed",          # 无控制台窗口
        "--icon", "pygit_icon.ico",
        "--clean",
        "--noconfirm",
    ]

    # 如果有内置 MinGit，一起打包进去
    if has_bundled_git:
        cmd += [
            f"--add-data={bundled_git_dir}{os.pathsep}bundled_git",
        ]
        print("✅ 检测到 bundled_git，将内置 Git 一起打包")
    else:
        print("⚠️  未检测到 bundled_git，EXE 将依赖系统 Git")

    cmd.append("git_gui.py")

    print("正在打包 PyGit.exe ...")
    print(f"命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=script_dir)

    if result.returncode == 0:
        exe_path = os.path.join(script_dir, "dist", "PyGit.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✅ 打包成功！")
            print(f"   文件: {exe_path}")
            print(f"   大小: {size_mb:.1f} MB")
        else:
            print("\n❌ 打包产物未找到")
    else:
        print(f"\n❌ 打包失败，退出码: {result.returncode}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(build())
