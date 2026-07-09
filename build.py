"""PyInstaller 打包脚本

将应用打包为独立可执行文件。
运行方式：python build.py

打包后的文件位于 dist/随机点名系统/ 目录下。
"""
import os
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# -------- 配置 --------
APP_NAME = "随机点名系统"
ENTRY_SCRIPT = "main.py"
ICON_FILE = "config/icon.ico"

# 需要打包进 exe 的资源文件（只读资源，通过 RESOURCE_DIR 访问）
DATAS = [
    ("config/icon.ico", "config"),
    ("config/ABOUT.md", "config"),
    ("config/data/PersonnelList.xlsx", "config/data"),
    ("README.md", "."),
]

# PyInstaller --add-data 在不同平台使用不同分隔符
_SEP = ";" if sys.platform == "win32" else ":"


def clean():
    """清理上次打包产物"""
    for name in ["build", "dist"]:
        path = PROJECT_ROOT / name
        if path.exists():
            shutil.rmtree(path)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
    print("[clean] 清理完成")


def build():
    """执行 PyInstaller 打包"""
    # 构建 --add-data 参数
    add_data_args = []
    for src, dest in DATAS:
        add_data_args.extend(["--add-data", f"{src}{_SEP}{dest}"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--icon", str(PROJECT_ROOT / ICON_FILE),
        *add_data_args,
        "--windowed",          # 不显示控制台窗口
        "--clean",             # 清理临时文件
        "--noconfirm",         # 覆盖输出目录不询问
        str(PROJECT_ROOT / ENTRY_SCRIPT),
    ]

    print(f"[build] 开始打包...")
    print(f"[build] {' '.join(cmd)}")
    print()

    # PyInstaller 会直接接管输出
    result = os.system(" ".join(cmd))
    if result != 0:
        print(f"\n[build] 打包失败，退出码: {result}")
        sys.exit(result)

    print(f"\n[build] 打包完成！")
    print(f"[build] 输出目录: {PROJECT_ROOT / 'dist' / APP_NAME}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PyInstaller 打包脚本")
    parser.add_argument("--clean-only", action="store_true", help="仅清理打包产物")
    args = parser.parse_args()

    if args.clean_only:
        clean()
    else:
        clean()
        build()


if __name__ == "__main__":
    main()
