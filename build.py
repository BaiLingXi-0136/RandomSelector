"""PyInstaller 打包脚本

将应用打包为独立可执行文件，嵌入版本信息等 Windows 资源属性。
运行方式：python build.py

打包后的文件位于 dist/RandomSelector/ 目录下。
"""
import os
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

# -------- 从应用常量读取版本信息 --------
sys.path.insert(0, str(PROJECT_ROOT))
from constants import APP_TITLE, APP_VERSION  # noqa: E402

# -------- 配置 --------
APP_NAME = "RandomSelector"
ENTRY_SCRIPT = "main.py"
ICON_FILE = "config/icon.ico"
VERSION_FILE = "config/version_info.txt"      # 自动生成：不要手动编辑

# 需要打包进 exe 的资源文件（只读资源，通过 RESOURCE_DIR 访问）
DATAS = [
    ("config/icon.ico", "config"),
    ("config/ABOUT.md", "config"),
    ("config/data/DefaultList.xlsx", "config/data"),
]

# PyInstaller --add-data 在不同平台使用不同分隔符
_SEP = ";" if sys.platform == "win32" else ":"


def generate_version_file():
    """根据 constants.py 中的 APP_VERSION 动态生成 Windows 版本信息文件

    这样只需修改 constants.py 一处，版本即同步到 EXE 属性。
    """
    # 解析版本号（支持 "4.3" → (4, 3, 0, 0) 和 "4.3.1" → (4, 3, 1, 0)）
    parts = [int(x) for x in APP_VERSION.split(".")]
    while len(parts) < 4:
        parts.append(0)
    ver_tuple = tuple(parts[:4])

    content = f"""# UTF-8
#
# 此文件由 build.py 自动生成，请勿手动编辑。
# 版本号来源于 constants.py 中的 APP_VERSION = "{APP_VERSION}"
#
# 参考: https://docs.microsoft.com/en-us/windows/win32/menurc/vs-versioninfo

VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,      # VFT_APP
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404b0',    # 中文简体, Unicode
        [
          StringStruct('CompanyName', 'ASUS'),
          StringStruct('FileDescription', '{APP_TITLE}'),
          StringStruct('FileVersion', '{APP_VERSION}'),
          StringStruct('InternalName', 'RandomSelector'),
          StringStruct('LegalCopyright', 'Copyright © 2025'),
          StringStruct('OriginalFilename', 'RandomSelector.exe'),
          StringStruct('ProductName', '{APP_TITLE}'),
          StringStruct('ProductVersion', '{APP_VERSION}'),
        ]
      )
    ]),
    VarFileInfo([
      VarStruct('Translation', [0x0804, 0x04b0])   # zh-CN
    ])
  ]
)
"""
    dest = PROJECT_ROOT / VERSION_FILE
    dest.write_text(content, encoding="utf-8")
    print(f"[build] 版本信息文件已生成: {dest}  (v{APP_VERSION})")


def clean():
    """清理上次打包产物"""
    for name in ["build", "dist"]:
        path = PROJECT_ROOT / name
        if path.exists():
            shutil.rmtree(path)
    for spec in PROJECT_ROOT.glob("*.spec"):
        spec.unlink()
    version_file = PROJECT_ROOT / VERSION_FILE
    if version_file.exists():
        version_file.unlink()
    print("[clean] 清理完成")


def build():
    """执行 PyInstaller 打包"""
    # 根据 constants.APP_VERSION 动态生成版本信息文件
    generate_version_file()

    # 构建 --add-data 参数
    add_data_args = []
    for src, dest in DATAS:
        add_data_args.extend(["--add-data", f"{src}{_SEP}{dest}"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--icon", str(PROJECT_ROOT / ICON_FILE),
        "--version-file", str(PROJECT_ROOT / VERSION_FILE),
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

    # 将 README.md 复制到 exe 所在目录（帮助对话框从中读取）
    dist_dir = PROJECT_ROOT / "dist" / APP_NAME
    readme_src = PROJECT_ROOT / "README.md"
    readme_dest = dist_dir / "README.md"
    try:
        shutil.copy2(readme_src, readme_dest)
        print(f"[build] README.md 已复制到 {readme_dest}")
    except OSError as e:
        print(f"[build] 复制 README.md 失败: {e}")

    print(f"\n[build] 打包完成！")
    print(f"[build] 输出目录: {dist_dir}")


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
