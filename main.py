"""程序入口"""
import flet as ft
from config import bootstrap, RESOURCE_DIR
from random_selector_ui import RandomSelectorUI


def main(page: ft.Page):
    """主函数"""
    # PyInstaller 打包后首次运行：将默认资源复制到可写目录
    bootstrap()

    page.title = "随机选择人员系统"
    page.theme_mode = ft.ThemeMode.LIGHT
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


if __name__ == "__main__":
    ft.app(target=main)
