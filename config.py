"""配置常量与设置文件读写

支持 PyInstaller 打包：通过 sys.frozen 判断运行环境，
区分可写数据目录（exe 旁）和只读资源目录（_MEIPASS）。
"""
import sys
import json
import shutil
from pathlib import Path


def get_base_path() -> Path:
    """可写数据目录：开发时为项目根目录，打包后为 exe 所在目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_resource_path() -> Path:
    """只读资源目录：开发时为项目根目录，打包后为 PyInstaller 临时解压目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


BASE_DIR = get_base_path()
RESOURCE_DIR = get_resource_path()

CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = CONFIG_DIR / "data"
DEFAULT_EXCEL_FILE = DATA_DIR / "PersonnelList.xlsx"
SETTINGS_FILE = CONFIG_DIR / "settings.json"


def bootstrap():
    """首次运行时，将默认资源文件从只读资源目录复制到可写数据目录"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 复制 ABOUT.md
    _copy_if_missing("ABOUT.md", RESOURCE_DIR / "config" / "ABOUT.md", CONFIG_DIR / "ABOUT.md")

    # 复制默认 Excel 文件
    _copy_if_missing(
        "PersonnelList.xlsx",
        RESOURCE_DIR / "config" / "data" / "PersonnelList.xlsx",
        DEFAULT_EXCEL_FILE,
    )


def _copy_if_missing(name: str, src: Path, dest: Path):
    """如果目标文件不存在且源文件存在，则复制"""
    if not dest.exists() and src.exists():
        try:
            shutil.copy2(src, dest)
        except OSError:
            pass  # 复制失败不阻塞启动


def load_settings() -> dict:
    """从设置文件读取所有配置"""
    try:
        if SETTINGS_FILE.exists():
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (Exception,):
        pass
    return {}


def save_settings(settings: dict):
    """保存配置到设置文件"""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # 合并现有设置，避免覆盖其他字段
        current = load_settings()
        current.update(settings)
        SETTINGS_FILE.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (Exception,):
        pass


def get_data_file_path() -> Path:
    """从设置获取数据文件路径，无效则返回默认"""
    settings = load_settings()
    path = Path(settings.get("data_file", str(DEFAULT_EXCEL_FILE)))
    return path if path.exists() else DEFAULT_EXCEL_FILE
