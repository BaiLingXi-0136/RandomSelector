"""程序入口"""
import sys
import ctypes
import flet as ft
from config import bootstrap, RESOURCE_DIR, load_settings, save_settings
from random_selector_ui import RandomSelectorUI
from ui_helpers import open_help_dialog

# 单实例互斥体名称（Local 前缀 = 仅当前用户会话，无需管理员权限）
_MUTEX_NAME = r"Local\RandomSelector_v4"
_mutex_handle = None  # 保持句柄引用，防止被 GC 回收导致互斥体提前释放


# noinspection PyUnresolvedReferences
def _ensure_single_instance() -> bool:
    """检查是否已有实例在运行。

    使用 Windows 命名互斥体。若互斥体已存在，说明已有实例运行中。
    返回 True 表示当前是唯一实例，False 表示已有其他实例。
    """
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    error = kernel32.GetLastError()
    if error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def main(page: ft.Page):
    """主函数"""
    # PyInstaller 打包后首次运行：将默认资源复制到可写目录
    bootstrap()

    page.title = "随机点名系统"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family="Microsoft YaHei")
    page.window.icon = str(RESOURCE_DIR / "config" / "icon.ico")

    # 设置页面布局
    page.window_width = 800
    page.window_height = 600
    page.window_resizable = True
    page.window.center()

    # 创建应用实例
    app_ui = RandomSelectorUI()

    # 构建主视图（内部创建 file_picker）
    main_view = app_ui.build_main_view()

    # 将文件选择器挂载到 overlay（必须在 page.add 之前，否则 pick_files 报错）
    page.overlay.append(app_ui.file_picker)

    # 将主视图添加到页面
    page.add(main_view)

    # 首次运行：弹出帮助界面
    settings = load_settings()
    if settings.get("first_run", True):
        save_settings({"first_run": False})
        open_help_dialog(page)

    # 启动文件占用实时监测
    app_ui.start_file_monitor(page)


if __name__ == "__main__":
    if not _ensure_single_instance():
        # 已有实例在运行，静默退出
        sys.exit(0)
    ft.app(target=main)
