"""后台下载管理器

检测到新版本后，从 GitHub Releases 下载安装包。
使用标准库 urllib / http.client，与 update_check.py 保持一致的网络模式。

DNS 劫持应对：与 update_check.py 相同，当检测到 GitHub 域名被 hosts 文件
指向 127.0.0.1 时，自动回退到真实 IP 直连。
"""
import json
import os
import socket
import ssl
import threading
import http.client
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable

from constants import (
    APP_VERSION,
    DOWNLOAD_ERROR_NETWORK,
    DOWNLOAD_ERROR_DISK_FULL,
    DOWNLOAD_ERROR_UNKNOWN,
    DOWNLOAD_ERROR_URL_RESOLVE,
    DOWNLOAD_STATUS_CANCELLED,
)

# ==================== 配置 ====================

_GITHUB_API_HOST = "api.github.com"
_GITHUB_HOST = "github.com"
_API_RELEASES_PATH = "/repos/BaiLingXi-0136/RandomSelector/releases/latest"
_REQUEST_TIMEOUT = 30  # 下载请求超时（秒），比检查更新长
_API_TIMEOUT = 15      # API 请求超时（秒）
_CHUNK_SIZE = 8192     # 下载流读取块大小

# GitHub Fastly CDN 真实 IP（用于 hosts 文件 DNS 劫持时回退）
# 与 update_check.py 使用相同的 IP 池
_FALLBACK_IPS = [
    "185.199.109.133",
    "185.199.108.133",
    "185.199.111.133",
    "185.199.110.133",
]

# 安装包文件名模式（与 build.py OutputBaseFilename 保持一致）
_SETUP_FILENAME_PATTERN = "RandomSelector_v{version}_Setup.exe"

# 回调类型
ProgressCallback = Callable[[int, int, str], None]  # (bytes_done, total, filename)
CompleteCallback = Callable[[str, str], None]       # (file_path, filename)
ErrorCallback = Callable[[str], None]               # (error_message)


# ==================== DNS 劫持检测 ====================

_dns_cache: dict[str, bool] = {}
_dns_checked: dict[str, bool] = {}


def _check_dns_poisoning(host: str) -> bool:
    """检测指定域名是否被 hosts 文件劫持到 127.0.0.1。

    结果按域名缓存，每个进程生命周期内只检测一次。
    """
    if _dns_checked.get(host, False):
        return _dns_cache.get(host, False)

    _dns_checked[host] = True
    try:
        addrs = socket.getaddrinfo(host, 443)
        for addr in addrs:
            ip = addr[4][0]
            if not ip.startswith("127.") and ip != "::1":
                _dns_cache[host] = False
                return False
        _dns_cache[host] = True
        return True
    except socket.gaierror:
        _dns_cache[host] = False
        return False


# ==================== URL 解析（混合策略） ====================


def _fetch_release_info_via_urllib() -> dict | None:
    """通过 GitHub API 获取最新 release 信息（DNS 正常时使用）。

    返回 dict: {"version": str, "download_url": str, "filename": str, "size": int}
    失败返回 None。
    """
    try:
        url = f"https://{_GITHUB_API_HOST}{_API_RELEASES_PATH}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", f"RandomSelector/{APP_VERSION}")
        req.add_header("Accept", "application/vnd.github+json")
        with urllib.request.urlopen(req, timeout=_API_TIMEOUT) as resp:
            content = resp.read().decode("utf-8")
        return _parse_github_api_response(content)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        socket.timeout,
        UnicodeDecodeError,
        json.JSONDecodeError,
        OSError,
    ):
        return None


def _fetch_release_info_via_ip_fallback() -> dict | None:
    """通过真实 IP 直连 GitHub API（DNS 被劫持时使用）。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    for ip in _FALLBACK_IPS:
        try:
            conn = http.client.HTTPSConnection(
                ip, timeout=_API_TIMEOUT, context=ctx,
            )
            conn.request("GET", _API_RELEASES_PATH, headers={
                "Host": _GITHUB_API_HOST,
                "User-Agent": f"RandomSelector/{APP_VERSION}",
                "Accept": "application/vnd.github+json",
            })
            resp = conn.getresponse()
            content = resp.read().decode("utf-8")
            conn.close()

            info = _parse_github_api_response(content)
            if info is not None:
                return info
        except (OSError, socket.timeout, UnicodeDecodeError,
                json.JSONDecodeError, ssl.SSLError):
            continue

    return None


def _parse_github_api_response(body: str) -> dict | None:
    """解析 GitHub API latest release 响应，提取下载信息。

    查找文件名匹配 "RandomSelector_v*_Setup.exe" 的 asset。
    """
    data = json.loads(body)
    tag_name = data.get("tag_name", "")
    assets = data.get("assets", [])

    # 查找安装包 asset（文件名模式: RandomSelector_v4.5.0_Setup.exe）
    for asset in assets:
        name = asset.get("name", "")
        if name.startswith("RandomSelector_v") and name.endswith("_Setup.exe"):
            return {
                "version": tag_name.lstrip("v"),
                "download_url": asset.get("browser_download_url", ""),
                "filename": name,
                "size": asset.get("size", 0),
            }

    # 没找到匹配的 asset，尝试用 tag_name 构造
    version = tag_name.lstrip("v")
    if version:
        return _construct_download_url(version)

    return None


def _construct_download_url(version: str) -> dict:
    """从版本号构造 GitHub Releases 下载 URL（回退策略）。

    模式: https://github.com/{owner}/{repo}/releases/download/v{version}/RandomSelector_v{version}_Setup.exe
    """
    filename = _SETUP_FILENAME_PATTERN.format(version=version)
    download_url = (
        f"https://github.com/BaiLingXi-0136/RandomSelector"
        f"/releases/download/v{version}/{filename}"
    )
    return {
        "version": version,
        "download_url": download_url,
        "filename": filename,
        "size": 0,  # 未知大小
    }


def resolve_download_url(version: str) -> dict:
    """解析下载 URL（混合策略）。

    1. 优先尝试 GitHub API（能获取文件大小和精确 URL）
    2. 失败则从版本号构造 URL（size=0 表示未知大小）

    始终返回包含 download_url / filename / size 的 dict。
    """
    # 1. DNS 劫持时直接走 IP 回退
    if _check_dns_poisoning(_GITHUB_API_HOST):
        result = _fetch_release_info_via_ip_fallback()
        if result is not None:
            return result
        return _construct_download_url(version)

    # 2. 标准 API 请求
    result = _fetch_release_info_via_urllib()
    if result is not None:
        return result

    # 3. API 失败，尝试 IP 回退
    result = _fetch_release_info_via_ip_fallback()
    if result is not None:
        return result

    # 4. 全部失败，构造 URL
    return _construct_download_url(version)


# ==================== 下载执行 ====================


def _download_via_urllib(
    url: str, dest_path: Path, total_size: int,
    progress_callback: ProgressCallback, cancel_flag: Callable[[], bool],
    filename: str,
) -> bool:
    """标准 urllib 流式下载（DNS 正常时使用）。"""
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", f"RandomSelector/{APP_VERSION}")
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            # 如果 API 返回了大小就用 API 的，否则用响应头的 Content-Length
            effective_size = total_size
            if effective_size <= 0:
                cl = resp.headers.get("Content-Length")
                if cl:
                    effective_size = int(cl)

            downloaded = 0
            with open(dest_path, "wb") as f:
                while True:
                    if cancel_flag():
                        return False
                    chunk = resp.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress_callback(downloaded, effective_size, filename)
        return True
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        socket.timeout,
        OSError,
    ):
        return False


def _download_via_ip_fallback(
    url: str, dest_path: Path, total_size: int,
    progress_callback: ProgressCallback, cancel_flag: Callable[[], bool],
    filename: str,
) -> bool:
    """通过 IP 直连流式下载（DNS 被劫持时使用）。

    从 URL 中解析出路径，通过 http.client 直连 IP 进行 HTTPS 请求。
    """
    # 从 URL 中解析 path: https://github.com/owner/repo/releases/download/vX/file.exe
    path_start = url.find("/", 8)  # skip "https://"
    if path_start < 0:
        return False
    request_path = url[path_start:]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # 判断重定向目标域名（可能是 github.com 或 objects.githubusercontent.com）
    host = _GITHUB_HOST

    for ip in _FALLBACK_IPS:
        try:
            conn = http.client.HTTPSConnection(
                ip, timeout=_REQUEST_TIMEOUT, context=ctx,
            )
            conn.request("GET", request_path, headers={
                "Host": host,
                "User-Agent": f"RandomSelector/{APP_VERSION}",
            })
            resp = conn.getresponse()

            # 处理重定向（GitHub Releases 通常会 302 到 S3）
            if resp.status in (301, 302):
                location = resp.headers.get("Location", "")
                conn.close()
                if location:
                    # 递归跟随重定向
                    return _download_via_urllib(
                        location, dest_path, total_size,
                        progress_callback, cancel_flag, filename,
                    )
                continue

            effective_size = total_size
            if effective_size <= 0:
                cl = resp.headers.get("Content-Length")
                if cl:
                    effective_size = int(cl)

            downloaded = 0
            with open(dest_path, "wb") as f:
                while True:
                    if cancel_flag():
                        conn.close()
                        return False
                    chunk = resp.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress_callback(downloaded, effective_size, filename)

            conn.close()
            return True
        except (OSError, socket.timeout, ssl.SSLError):
            continue

    return False


def _perform_download(
    download_url: str, dest_path: Path, total_size: int,
    progress_callback: ProgressCallback, cancel_flag: Callable[[], bool],
    filename: str,
) -> bool:
    """执行下载：DNS 正常走 urllib，被劫持走 IP 回退。"""
    # 判断 URL 对应的 host
    if "objects.githubusercontent.com" in download_url:
        host = "objects.githubusercontent.com"
    elif "github.com" in download_url:
        host = _GITHUB_HOST
    else:
        host = _GITHUB_HOST

    if _check_dns_poisoning(host):
        return _download_via_ip_fallback(
            download_url, dest_path, total_size,
            progress_callback, cancel_flag, filename,
        )

    success = _download_via_urllib(
        download_url, dest_path, total_size,
        progress_callback, cancel_flag, filename,
    )
    if success:
        return True

    # 标准方式失败，尝试 IP 回退
    return _download_via_ip_fallback(
        download_url, dest_path, total_size,
        progress_callback, cancel_flag, filename,
    )


# ==================== DownloadManager ====================


def _get_downloads_folder() -> Path:
    """获取用户 Downloads 文件夹路径。"""
    if os.name == "nt":
        userprofile = os.environ.get("USERPROFILE", "")
        downloads = Path(userprofile) / "Downloads"
        if downloads.exists():
            return downloads
    home = Path.home()
    downloads = home / "Downloads"
    return downloads if downloads.exists() else home


def _unique_dest_path(dest_dir: Path, filename: str) -> Path:
    """生成唯一的目标文件路径，若文件已存在则追加数字后缀。"""
    dest = dest_dir / filename
    if not dest.exists():
        return dest

    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    ext = "." + filename.rsplit(".", 1)[1] if "." in filename else ""
    counter = 1
    while True:
        dest = dest_dir / f"{stem} ({counter}){ext}"
        if not dest.exists():
            return dest
        counter += 1


class DownloadManager:
    """后台下载管理器。

    在后台线程中执行下载，通过回调通知进度 / 完成 / 错误。
    支持取消下载（线程安全）。
    """

    def __init__(self):
        self._cancel_flag = False
        self._thread: threading.Thread | None = None

    def start_download(
        self,
        version: str,
        dest_dir: Path | None = None,
        on_progress: ProgressCallback = lambda *a: None,
        on_complete: CompleteCallback = lambda *a: None,
        on_error: ErrorCallback = lambda *a: None,
    ):
        """启动后台下载。

        Args:
            version: 目标版本号（如 "4.5.0"）
            dest_dir: 下载目录，默认为用户 Downloads 文件夹
            on_progress: 进度回调 (bytes_done, total, filename)
            on_complete: 完成回调 (file_path, filename)
            on_error: 错误回调 (error_message)
        """
        if self._thread is not None and self._thread.is_alive():
            return  # 已经在下载中，忽略

        if dest_dir is None:
            dest_dir = _get_downloads_folder()

        self._cancel_flag = False

        def _run():
            try:
                # 1. 解析下载 URL
                info = resolve_download_url(version)
                download_url = info.get("download_url", "")
                filename = info.get("filename", "")
                total_size = info.get("size", 0)

                if not download_url or not filename:
                    on_error(DOWNLOAD_ERROR_URL_RESOLVE)
                    return

                # 2. 确定目标路径
                dest_path = _unique_dest_path(dest_dir, filename)

                # 3. 下载
                ok = _perform_download(
                    download_url, dest_path, total_size,
                    on_progress,
                    lambda: self._cancel_flag,
                    filename,
                )

                if ok:
                    on_complete(str(dest_path), filename)
                else:
                    # 取消？
                    if self._cancel_flag:
                        # 删除部分下载的文件
                        _safe_remove(dest_path)
                        on_error(DOWNLOAD_STATUS_CANCELLED)
                    else:
                        _safe_remove(dest_path)
                        on_error(DOWNLOAD_ERROR_NETWORK)

            except OSError as e:
                # 磁盘满等系统错误
                if hasattr(e, 'errno') and e.errno == 28:  # ENOSPC
                    on_error(DOWNLOAD_ERROR_DISK_FULL)
                else:
                    on_error(DOWNLOAD_ERROR_UNKNOWN.format(str(e)))
            except Exception as e:
                on_error(DOWNLOAD_ERROR_UNKNOWN.format(str(e)))

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def cancel_download(self):
        """取消正在进行的下载（线程安全）。"""
        self._cancel_flag = True

    def is_downloading(self) -> bool:
        """检查是否正在下载中。"""
        return self._thread is not None and self._thread.is_alive()


def _safe_remove(path: Path):
    """安全删除文件，忽略文件不存在的错误。"""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
