"""对话框构建器

集中管理所有 AlertDialog 的创建，保持 UI 层精简。
"""
import flet as ft
from typing import Callable

from config import BASE_DIR, RESOURCE_DIR
from constants import (
    BTN_CANCEL, BTN_CONFIRM, COLOR_HINT, COLOR_SUBTLE,
    FONT_SIZE_HINT, HINT_SEED, SEED_INPUT_WIDTH,
)


# ==================== 关于 / 帮助 ====================

def show_about_dialog(page: ft.Page):
    """打开关于对话框（内容从 ABOUT.md 读取）"""
    about_path = RESOURCE_DIR / "config" / "ABOUT.md"
    try:
        about_text = about_path.read_text(encoding="utf-8")
    except OSError:
        about_text = "无法加载关于信息"

    dialog = ft.AlertDialog(
        title=ft.Text("关于"),
        content=ft.Container(
            ft.Markdown(
                about_text,
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            ),
            width=500,
        ),
        actions=[
            ft.TextButton(BTN_CONFIRM, on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


def on_menu_about(e):
    """菜单栏事件处理器：打开关于对话框"""
    show_about_dialog(e.page)


def open_help_dialog(page: ft.Page):
    """在给定 page 上打开使用说明对话框（内容从 README.md 读取）"""
    # 优先从资源目录查找（开发模式），其次从 exe 所在目录查找（打包后）
    for base in (RESOURCE_DIR, BASE_DIR):
        readme_path = base / "README.md"
        if readme_path.exists():
            try:
                help_text = readme_path.read_text(encoding="utf-8")
                break
            except OSError:
                continue
    else:
        help_text = "无法加载使用说明"

    dialog = ft.AlertDialog(
        title=ft.Text("使用说明"),
        content=ft.Column(
            [
                ft.Markdown(
                    help_text,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            width=700,
            height=450,
        ),
        actions=[
            ft.TextButton(BTN_CONFIRM, on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


def on_menu_help(e):
    """菜单栏事件处理器：打开使用说明对话框"""
    open_help_dialog(e.page)


# ==================== 选项（种子）对话框 ====================

def show_options_dialog(
    page: ft.Page,
    seed_enabled: bool,
    seed_value: int,
    on_save: Callable[[bool, int], None],
):
    """打开选项配置对话框，用户确认后通过 on_save 回调保存"""

    seed_checkbox = ft.Checkbox(
        label="启用固定种子 (Seed)",
        value=seed_enabled,
    )
    seed_input = ft.TextField(
        label="种子值",
        value=str(seed_value),
        width=SEED_INPUT_WIDTH,
        keyboard_type=ft.KeyboardType.NUMBER,
        text_align=ft.TextAlign.CENTER,
        disabled=not seed_enabled,
    )

    def on_checkbox_change(_e):
        seed_input.disabled = not seed_checkbox.value
        seed_input.update()

    seed_checkbox.on_change = on_checkbox_change

    def on_confirm(_e):
        try:
            val = int(seed_input.value)
            if val < 0:
                raise ValueError
        except ValueError:
            seed_input.error_text = "请输入非负整数"
            seed_input.update()
            return

        page.close(dialog)
        on_save(seed_checkbox.value, val)

    def on_cancel(_e):
        page.close(dialog)

    dialog = ft.AlertDialog(
        title=ft.Text("选项"),
        content=ft.Column(
            [
                seed_checkbox,
                ft.Row([ft.Text("种子值："), seed_input]),
                ft.Text(
                    HINT_SEED,
                    size=FONT_SIZE_HINT,
                    color=COLOR_SUBTLE,
                    italic=True,
                ),
            ],
            tight=True,
        ),
        actions=[
            ft.TextButton(BTN_CANCEL, on_click=on_cancel),
            ft.TextButton(BTN_CONFIRM, on_click=on_confirm),
        ],
    )
    page.open(dialog)


# ==================== 确认对话框 ====================

def show_confirm_dialog(
    page: ft.Page,
    title: str,
    content: str,
    confirm_label: str,
    on_confirm: Callable[[], None],
    on_cancel: Callable[[], None] | None = None,
):
    """通用确认对话框"""
    def _confirm(_e):
        page.close(dialog)
        on_confirm()

    def _cancel(_e):
        page.close(dialog)
        if on_cancel:
            on_cancel()

    dialog = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(content),
        actions=[
            ft.TextButton(BTN_CANCEL, on_click=_cancel),
            ft.TextButton(confirm_label, on_click=_confirm),
        ],
    )
    page.open(dialog)


def show_clear_records_confirm(page: ft.Page, on_confirm: Callable[[], None]):
    """清空记录确认对话框"""
    show_confirm_dialog(
        page=page,
        title="确认清空",
        content="确定要清空所有选择记录吗？\n此操作不可撤销，所有人员的选中状态将被重置。",
        confirm_label="确定清空",
        on_confirm=on_confirm,
    )


def show_mopping_redo_confirm(page: ft.Page, on_confirm: Callable[[], None]):
    """拖地模式重新抽选确认对话框"""
    show_confirm_dialog(
        page=page,
        title="今日已抽选",
        content=(
            "今天已经进行过一次拖地模式抽选。\n"
            "若确认重新抽选，将清除最近3条拖地记录并重新随机选择3人。\n\n"
            "确定要继续吗？"
        ),
        confirm_label="确认重新抽选",
        on_confirm=on_confirm,
    )
