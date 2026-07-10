"""全局异常捕获

在 PyInstaller --windowed 模式下控制台不可见，未处理异常会导致程序静默退出。

Flet 内部将同步事件处理器（on_click 等）通过 ThreadPoolExecutor 执行，
异常被 Future 吞掉，sys.excepthook 无法捕获。本模块通过以下机制解决：

 1. Monkey-patch Page.__context_wrapper — 拦截所有事件处理器异常（主路径）
 2. sys.excepthook — 兜底，处理 Flet 事件循环之外的异常（如后台线程）

异常发生时会：
 - 将完整 Traceback 写入 config/logs/error_YYYYMMDD_HHMMSS.log
 - 在 Flet 页面上弹窗提示用户
"""
import functools
import sys
import traceback
from datetime import datetime
from pathlib import Path

import flet as ft

from config import BASE_DIR
from constants import (
    BTN_CONFIRM, COLOR_DANGER, COLOR_ERROR_BG,
    FONT_SIZE_SMALL, FONT_SIZE_BODY, MAX_LOG_FILES,
)

# ---------- 日志目录 ----------
LOG_DIR = BASE_DIR / "config" / "logs"

# 保存 page 引用
_page_ref: ft.Page | None = None
_original_excepthook = None


def setup_error_handler(page: ft.Page) -> None:
    """注册全局异常钩子。应在 main(page) 中尽早调用。"""
    global _page_ref, _original_excepthook
    _page_ref = page

    # 主路径：拦截 Flet 内部事件处理器中的异常
    _patch_flet_handler(page)

    # 兜底：Flet 事件循环之外的异常（如后台线程）
    if _original_excepthook is None:
        _original_excepthook = sys.excepthook
    sys.excepthook = _exception_hook


# ---------------------------------------------------------------------------
# Monkey-patch Flet 内部事件分发
# ---------------------------------------------------------------------------

def _patch_flet_handler(page: ft.Page) -> None:
    """替换 Page.__context_wrapper，在用户回调外层包裹异常捕获。

    Flet 的 run_thread 通过 __context_wrapper → ThreadPoolExecutor 执行同步
    事件处理器，异常被 Future 吞掉。这里在 wrapper 层加上 try/except 解决。
    若未来 Flet 版本变更导致属性名不兼容，静默降级（至少 sys.excepthook 仍在）。
    """
    try:
        # Python name mangling: __context_wrapper → _Page__context_wrapper
        _original_wrapper = page._Page__context_wrapper  # noqa: SLF001
    except AttributeError:
        return

    def _patched_wrapper(handler):
        wrapped = _original_wrapper(handler)

        @functools.wraps(wrapped)
        def safe_wrapper(*args):
            try:
                wrapped(*args)
            except Exception:
                _handle_flet_exception(*sys.exc_info())

        return safe_wrapper

    page._Page__context_wrapper = _patched_wrapper  # noqa: SLF001


# ---------------------------------------------------------------------------
# 统一的异常处理入口
# ---------------------------------------------------------------------------

def _handle_flet_exception(exc_type, exc_value, exc_tb) -> None:
    """处理来自 Flet 事件循环的异常。"""
    # 1. 写入日志
    log_path = _write_exception_log(exc_type, exc_value, exc_tb)

    # 2. 弹窗
    _show_error_dialog(exc_type, exc_value, log_path)


# ---------------------------------------------------------------------------
# sys.excepthook 兜底
# ---------------------------------------------------------------------------

def _exception_hook(exc_type, exc_value, exc_tb):
    """sys.excepthook 回调 — Flet 事件循环之外的异常。"""
    log_path = _write_exception_log(exc_type, exc_value, exc_tb)
    _show_error_dialog(exc_type, exc_value, log_path)

    if _original_excepthook is not None:
        _original_excepthook(exc_type, exc_value, exc_tb)


# ---------------------------------------------------------------------------
# 日志写入
# ---------------------------------------------------------------------------

def _write_exception_log(exc_type, exc_value, exc_tb) -> Path | None:
    """将异常 Traceback 写入带时间戳的日志文件。"""
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"error_{timestamp}.log"
        log_path = LOG_DIR / filename

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        full_tb = "".join(tb_lines)

        content = (
            f"错误发生时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"══════════════════════════════════════════════\n\n"
            f"{full_tb}\n"
            f"══════════════════════════════════════════════\n"
        )

        log_path.write_text(content, encoding="utf-8")
        _cleanup_old_logs()
        return log_path
    except Exception:
        return None


def _cleanup_old_logs() -> None:
    """删除超出数量限制的旧错误日志。"""
    try:
        log_files = sorted(LOG_DIR.glob("error_*.log"), key=lambda p: p.stat().st_mtime)
        while len(log_files) > MAX_LOG_FILES:
            oldest = log_files.pop(0)
            oldest.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 错误弹窗
# ---------------------------------------------------------------------------

def _show_error_dialog(exc_type, exc_value, log_path: Path | None) -> None:
    """在 Flet 页面上弹出错误提示对话框。

    整个函数用 try/except 包裹——错误处理本身绝不应再抛异常。
    """
    page = _page_ref
    if page is None:
        return

    try:
        error_type = exc_type.__name__ if exc_type else "UnknownError"
        error_message = str(exc_value) if exc_value else "(无详细描述)"

        # 完整 Traceback 文本
        tb_text = "".join(
            traceback.format_exception(exc_type, exc_value, exc_value.__traceback__)
        )

        # 弹窗中的显示内容：截取前 30 行
        tb_lines = tb_text.strip().split("\n")
        truncated = len(tb_lines) > 30
        if truncated:
            tb_lines = tb_lines[:30]
            tb_lines.append("... （完整信息已写入日志文件）")
        tb_display = "\n".join(tb_lines)

        log_info = f"\n\n📄 日志文件已保存至：\n{log_path}" if log_path else ""

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color=COLOR_DANGER, size=24),
                    ft.Text(
                        "程序错误", size=FONT_SIZE_BODY,
                        weight=ft.FontWeight.BOLD, color=COLOR_DANGER,
                    ),
                ],
                spacing=8,
            ),
            content=ft.Column(
                [
                    ft.Container(
                        ft.Text(
                            f"❌ {error_type}：{error_message}{log_info}",
                            size=FONT_SIZE_SMALL,
                            selectable=True,
                        ),
                        bgcolor=COLOR_ERROR_BG,
                        border_radius=8,
                        padding=12,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    tb_display,
                                    size=11,
                                    selectable=True,
                                    color="#555555",
                                ),
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            height=240,
                        ),
                        bgcolor="#fafafa",
                        border=ft.border.all(1, "#e0e0e0"),
                        border_radius=8,
                        padding=12,
                        margin=ft.Margin(top=8, bottom=0, left=0, right=0),
                    ),
                ],
                scroll=ft.ScrollMode.AUTO,
                width=600,
                height=400,
            ),
            actions=[
                ft.TextButton(
                    BTN_CONFIRM,
                    on_click=lambda e: _close_dialog(e.page, dialog),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.open(dialog)
    except Exception:
        pass


def _close_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """关闭错误对话框。"""
    try:
        page.close(dialog)
    except Exception:
        pass
