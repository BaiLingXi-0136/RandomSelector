"""程序入口"""
import sys
import ctypes
import flet as ft
from config import bootstrap, RESOURCE_DIR, load_settings, save_settings
from constants import APP_TITLE, FONT_FAMILY, MUTEX_NAME, WINDOW_WIDTH, WINDOW_HEIGHT
from error_handler import setup_error_handler
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
    setup_error_handler(page)

    page.title = APP_TITLE
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(font_family=FONT_FAMILY)
    page.window.icon = str(RESOURCE_DIR / "config" / "icon.ico")

    # -- 屏幕自适应窗口尺寸 ---------------------------------------------------
    # 问题背景：Flet 的 window_width/height 使用"逻辑像素"（device-independent
    # pixels），而高 DPI 下每个逻辑像素映射到多个物理像素。如 300% DPI 时
    # 600 逻辑像素 = 1800 物理像素，在 2160 高的屏幕上几乎撑满，加上标题栏
    # 和任务栏就会溢出屏幕。
    #
    # 解决思路：
    #   1. GetDpiForSystem() 获取系统 DPI → 算出 device_pixel_ratio
    #   2. IsProcessDPIAware() 判断 GetSystemMetrics 返回的是物理还是虚拟像素
    #   3. 换算到同一坐标空间后，将窗口物理尺寸限制在屏幕 80%(高)/85%(宽) 以内
    #   4. 再换算回逻辑像素传给 Flet
    # ---------------------------------------------------------------------------
    user32 = ctypes.windll.user32

    # 获取系统 DPI（Windows 10 1607+），失败则回退到 96
    try:
        dpi = user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    scale = dpi / 96.0  # 1.0=100%, 1.5=150%, 3.0=300%

    # 判断当前进程是否声明了 DPI 感知
    try:
        is_dpi_aware = bool(user32.IsProcessDPIAware())
    except Exception:
        is_dpi_aware = False

    # 获取屏幕尺寸（物理 or 虚拟，取决于进程 DPI 感知状态）
    raw_w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    raw_h = user32.GetSystemMetrics(1)  # SM_CYSCREEN

    # 统一换算为物理像素
    if is_dpi_aware:
        phys_w, phys_h = raw_w, raw_h          # 已经是物理像素
    else:
        phys_w, phys_h = int(raw_w * scale), int(raw_h * scale)

    # 窗口物理尺寸上限（高 80%、宽 85%，为标题栏和任务栏留余量）
    max_phys_w = int(phys_w * 0.85)
    max_phys_h = int(phys_h * 0.80)

    # 换算回逻辑像素（与 Flet 坐标空间一致）
    max_logical_w = int(max_phys_w / scale)
    max_logical_h = int(max_phys_h / scale)

    # 实际窗口尺寸 = 设计尺寸与屏幕上限取较小值
    actual_width = min(WINDOW_WIDTH, max_logical_w)
    actual_height = min(WINDOW_HEIGHT, max_logical_h)

    page.window_width = actual_width
    page.window_height = actual_height
    page.window_min_width = min(actual_width, 480)
    page.window_min_height = min(actual_height, 340)
    page.window.max_width = max_logical_w
    page.window.max_height = max_logical_h
    page.window_resizable = True
    page.window.center()

    app_ui = RandomSelectorUI()
    main_view = app_ui.build_main_view()

    page.overlay.append(app_ui.file_picker)
    page.overlay.append(app_ui.md_file_picker)
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
