"""测试 EXE 内置 Git 是否正常"""
import subprocess, os, tempfile, shutil

exe = os.path.join(os.path.dirname(__file__), "dist", "PyGit.exe")
test_dir = os.path.join(tempfile.gettempdir(), "pygit_test_repo")

# 清理
if os.path.isdir(test_dir):
    shutil.rmtree(test_dir)
os.makedirs(test_dir)

print(f"测试目录: {test_dir}")

# 直接用内置 git 初始化测试
git_cmd = os.path.join(os.path.dirname(exe), "..", "bundled_git", "cmd", "git.exe")
if not os.path.isfile(git_cmd):
    # 打包后路径
    git_cmd = "git"

print(f"Git 路径: {git_cmd}")

# 测试 git version
r = subprocess.run([git_cmd, "version"], capture_output=True, text=True)
print(f"Git version: {r.stdout.strip()}")

# 测试 init
r = subprocess.run([git_cmd, "init"], cwd=test_dir, capture_output=True, text=True)
print(f"Init: {'OK' if r.returncode == 0 else 'FAIL'} - {r.stdout.strip() or r.stderr.strip()}")

# 测试 add + commit
test_file = os.path.join(test_dir, "hello.txt")
with open(test_file, "w") as f:
    f.write("hello from PyGit test")

subprocess.run([git_cmd, "add", "."], cwd=test_dir)
subprocess.run([git_cmd, "-c", "user.name=Test", "-c", "user.email=test@test.com", "commit", "-m", "test"], cwd=test_dir, capture_output=True, text=True)

# 测试 log
r = subprocess.run([git_cmd, "log", "--oneline"], cwd=test_dir, capture_output=True, text=True)
print(f"Log: {r.stdout.strip()}")

# 清理
shutil.rmtree(test_dir)
print("\n测试完成！" if r.returncode == 0 else "\n测试失败")
