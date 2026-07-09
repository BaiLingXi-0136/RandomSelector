"""程序入口"""
import sys
import ctypes
import flet as ft
from config import bootstrap, RESOURCE_DIR, load_settings, save_settings
from constants import APP_TITLE, FONT_FAMILY, MUTEX_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
from random_selector_ui import RandomSelectorUI
from dialogs import open_help_dialog

_mutex_handle = None  # 保持句柄引用，防止被 GC 回收导致互斥体提前释放


# noinspection PyUnresolvedReferences
def _ensure_single_instance() -> bool:
    """检查是否已有实例在运行。

    使用 Windows 命名互斥体。若互斥体已存在，说明已有实例运行中。
    返回 True 表示当前是唯一实例，False 表示已有其他实例。
    """
    global _mutex_handle
    kernel32 = ctypes.windll.kernel32
    _mutex_handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    error = kernel32.GetLastError()
    if error == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def main(page: ft.Page):
    """主函数"""
    bootstrap()

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family=FONT_FAMILY)
    page.window.icon = str(RESOURCE_DIR / "config" / "icon.ico")

    page.window_width = WINDOW_WIDTH
    page.window_height = WINDOW_HEIGHT
    page.window_resizable = True
    page.window.center()

    app_ui = RandomSelectorUI()
    main_view = app_ui.build_main_view()

    page.overlay.append(app_ui.file_picker)
    page.add(main_view)

    # 首次运行：弹出帮助界面
    settings = load_settings()
    if settings.get("first_run", True):
        save_settings({"first_run": False})
        open_help_dialog(page)

    # 启动文件占用实时监测
    app_ui.setup_file_monitor()


if __name__ == "__main__":
    if not _ensure_single_instance():
        sys.exit(0)
    ft.app(target=main)
