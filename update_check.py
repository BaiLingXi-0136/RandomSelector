"""更新检查模块

从 GitHub 仓库拉取远程 constants.py，解析 APP_VERSION 并与本地版本比对。
使用标准库 urllib，无需额外依赖。网络异常静默处理，不阻断正常使用。

DNS 劫持应对：当检测到 GitHub 域名被 hosts 文件指向 127.0.0.1
（如 Steam++ / Watt Toolkit 未运行时）时，自动回退到真实 IP 直连。
"""
import re
import socket
import ssl
import threading
import time
import http.client
import urllib.request
import urllib.error
from typing import Callable

import flet as ft

from constants import (
    APP_VERSION, BTN_CONFIRM,
    UPDATE_TITLE_AVAILABLE, UPDATE_TITLE_LATEST, UPDATE_TITLE_FAILED,
    UPDATE_MSG_AVAILABLE, UPDATE_MSG_LATEST,
    UPDATE_MSG_NETWORK_ERROR, UPDATE_MSG_PARSE_ERROR,
    COLOR_ERROR_BG, COLOR_INFO_BG, COLOR_SUCCESS_BG,
    COLOR_SUBTLE,
)

# 回调类型：on_result(status, version)
# status: "latest" | "update_available" | "error"
# version: 远程版本号（仅 "update_available" 时有值）
UpdateResultCallback = Callable[[str, str | None], None] | None

# ==================== 配置 ====================

_RAW_HOST = "raw.githubusercontent.com"
_RAW_PATH = "/BaiLingXi-0136/RandomSelector/main/constants.py"
REQUEST_TIMEOUT = 10  # 请求超时（秒）

# GitHub raw CDN 真实 IP（用于 hosts 文件 DNS 劫持时回退）
_FALLBACK_IPS = [
    "185.199.109.133",
    "185.199.108.133",
    "185.199.111.133",
    "185.199.110.133",
]

# ==================== DNS 劫持检测 ====================

_dns_poison_checked = False
_dns_is_poisoned = False


def _check_dns_poisoning() -> bool:
    """检测 raw.githubusercontent.com 是否被 hosts 文件劫持到 127.0.0.1。

    结果会被缓存（每个进程只检测一次），因为 hosts 文件在进程生命周期内不会变。
    """
    global _dns_poison_checked, _dns_is_poisoned
    if _dns_poison_checked:
        return _dns_is_poisoned

    _dns_poison_checked = True
    try:
        addrs = socket.getaddrinfo(_RAW_HOST, 443)
        for addr in addrs:
            ip = addr[4][0]
            if not ip.startswith("127.") and ip != "::1":
                _dns_is_poisoned = False
                return False
        _dns_is_poisoned = True
        return True
    except socket.gaierror:
        _dns_is_poisoned = False
        return False


# ==================== 内部函数 ====================


def _parse_version(version_str: str) -> tuple[int, ...]:
    """将版本号字符串解析为可比较的元组，解析失败返回空元组"""
    try:
        return tuple(int(seg) for seg in version_str.strip().split("."))
    except (ValueError, AttributeError):
        return ()


def _fetch_via_urllib() -> str | None:
    """标准 urllib 请求（DNS 正常时使用）"""
    try:
        url = f"https://{_RAW_HOST}{_RAW_PATH}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", f"RandomSelector/{APP_VERSION}")
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            content = resp.read().decode("utf-8")
        return _extract_version(content)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        socket.timeout,
        UnicodeDecodeError,
        UnicodeEncodeError,
        OSError,
    ):
        return None


def _fetch_via_ip_fallback() -> str | None:
    """通过真实 IP 直连 GitHub CDN（DNS 被劫持时使用）。

    使用 http.client 直连 IP，绕过 hosts 文件的 127.0.0.1 劫持。
    需要跳过 SSL 证书验证（证书绑定的域名不是 IP）。
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for ip in _FALLBACK_IPS:
        try:
            conn = http.client.HTTPSConnection(
                ip, timeout=REQUEST_TIMEOUT, context=ctx,
            )
            conn.request("GET", _RAW_PATH, headers={
                "Host": _RAW_HOST,
                "User-Agent": f"RandomSelector/{APP_VERSION}",
            })
            resp = conn.getresponse()
            content = resp.read().decode("utf-8")
            conn.close()

            version = _extract_version(content)
            if version is not None:
                return version
        except (OSError, socket.timeout, UnicodeDecodeError,
                UnicodeEncodeError, ssl.SSLError):
            continue

    return None


def _extract_version(content: str) -> str | None:
    """从 constants.py 内容中提取 APP_VERSION"""
    match = re.search(r'APP_VERSION\s*=\s*"([^"]*)"', content)
    if match:
        return match.group(1)
    return None


def _fetch_remote_version() -> str | None:
    """从 GitHub raw 拉取 constants.py 并提取 APP_VERSION。

    先尝试标准方式；若 DNS 被劫持则回退到 IP 直连。
    返回远程版本字符串（如 "4.5.0"），任何失败返回 None。
    """
    # 1. 有 DNS 劫持时直接走 IP 回退（urllib 的 HTTPS 在 127.0.0.1 上会超时）
    if _check_dns_poisoning():
        return _fetch_via_ip_fallback()

    # 2. 正常 DNS：标准 urllib 请求
    result = _fetch_via_urllib()
    if result is not None:
        return result

    # 3. 标准请求失败，再试一次 IP 回退（应对 DNS 解析成功但连接被阻的情况）
    return _fetch_via_ip_fallback()


# ==================== 对话框 ====================


def _show_loading_dialog(page: ft.Page) -> ft.AlertDialog:
    """弹出加载等待对话框，返回 dialog 对象供后续关闭"""
    dialog = ft.AlertDialog(
        title=ft.Text("检查更新"),
        content=ft.Row(
            [
                ft.ProgressRing(width=24, height=24),
                ft.Text("  正在检查更新...", color=COLOR_SUBTLE),
            ],
            tight=True,
        ),
        modal=True,
    )
    page.open(dialog)
    return dialog


def _show_update_available_dialog(page: ft.Page, remote_version: str):
    """弹出"发现新版本"对话框"""
    dialog = ft.AlertDialog(
        title=ft.Text(UPDATE_TITLE_AVAILABLE),
        content=ft.Text(
            UPDATE_MSG_AVAILABLE.format(
                version=remote_version, current=APP_VERSION
            ),
        ),
        content_padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=COLOR_SUCCESS_BG,
        actions=[
            ft.TextButton(BTN_CONFIRM, on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


def _show_already_latest_dialog(page: ft.Page):
    """弹出"已是最新版本"对话框"""
    dialog = ft.AlertDialog(
        title=ft.Text(UPDATE_TITLE_LATEST),
        content=ft.Text(UPDATE_MSG_LATEST.format(version=APP_VERSION)),
        content_padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=COLOR_INFO_BG,
        actions=[
            ft.TextButton(BTN_CONFIRM, on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


def _show_check_failed_dialog(page: ft.Page, message: str):
    """弹出"检查更新失败"对话框"""
    dialog = ft.AlertDialog(
        title=ft.Text(UPDATE_TITLE_FAILED),
        content=ft.Text(message),
        content_padding=ft.padding.symmetric(horizontal=24, vertical=20),
        bgcolor=COLOR_ERROR_BG,
        actions=[
            ft.TextButton(BTN_CONFIRM, on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


# ==================== 核心逻辑 ====================


def _do_check(page: ft.Page, silent_on_latest: bool,
              loading_dialog: ft.AlertDialog | None,
              on_result: UpdateResultCallback):
    """在后台线程中执行实际的网络检查并更新 UI。

    先关闭 loading_dialog（如有），再根据结果弹窗并调用 on_result。
    """
    remote_version = _fetch_remote_version()

    # 关闭加载对话框
    if loading_dialog is not None:
        page.close(loading_dialog)

    if remote_version is None:
        if not silent_on_latest:
            _show_check_failed_dialog(page, UPDATE_MSG_NETWORK_ERROR)
        if on_result:
            on_result("error", None)
        return

    remote_tuple = _parse_version(remote_version)
    local_tuple = _parse_version(APP_VERSION)

    if not remote_tuple or not local_tuple:
        if not silent_on_latest:
            _show_check_failed_dialog(page, UPDATE_MSG_PARSE_ERROR)
        if on_result:
            on_result("error", None)
        return

    if remote_tuple > local_tuple:
        _show_update_available_dialog(page, remote_version)
        if on_result:
            on_result("update_available", remote_version)
    else:
        if not silent_on_latest:
            _show_already_latest_dialog(page)
        if on_result:
            on_result("latest", None)


# ==================== 公共接口 ====================


def check_for_updates(
    page: ft.Page,
    silent_on_latest: bool = False,
    on_result: UpdateResultCallback = None,
):
    """检查更新（异步，不阻塞 UI）。

    弹出加载等待窗口 → 后台拉取版本 → 关闭加载窗口 → 弹窗通知结果。

    Args:
        page: Flet Page 实例
        silent_on_latest: 已是新版时是否弹窗（自动检查用 True）
        on_result: 结果回调，用于更新窗口内状态文字
    """
    loading_dialog = _show_loading_dialog(page)

    def _run():
        _do_check(page, silent_on_latest, loading_dialog, on_result)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def check_for_updates_async(
    page: ft.Page,
    delay: float = 3.0,
    silent_on_latest: bool = True,
    on_result: UpdateResultCallback = None,
):
    """启动时后台自动检查更新（无加载窗口，延迟执行）。

    Args:
        page: Flet Page 实例
        delay: 延迟秒数
        silent_on_latest: 已是新版时是否静默
        on_result: 结果回调
    """
    def _run():
        time.sleep(delay)
        _do_check(page, silent_on_latest, loading_dialog=None, on_result=on_result)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
