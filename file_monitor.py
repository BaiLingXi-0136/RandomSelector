"""文件占用实时监测

在后台线程中周期性地检测 Excel 数据文件是否可写，
通过回调通知 UI 层文件占用状态的变化。
"""
import threading
import time
from pathlib import Path
from typing import Callable

from constants import FILE_MONITOR_INTERVAL


class FileLockMonitor:
    """监测数据文件是否被外部程序占用（无法写入）。

    使用方式::

        monitor = FileLockMonitor(
            get_file_path=lambda: manager.file_path,
            on_locked=handle_locked,
            on_unlocked=handle_unlocked,
        )
        monitor.start()
        # ... 程序退出前调用 monitor.stop()
    """

    def __init__(
        self,
        get_file_path: Callable[[], Path],
        on_locked: Callable[[], None],
        on_unlocked: Callable[[], None],
    ):
        self._get_file_path = get_file_path
        self._on_locked = on_locked
        self._on_unlocked = on_unlocked
        self._locked = False
        self._running = False
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def start(self):
        """启动后台监测线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """停止监测线程"""
        self._running = False

    @property
    def is_locked(self) -> bool:
        """当前是否处于文件占用状态"""
        return self._locked

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _check_writable(self) -> bool:
        """检测当前数据文件是否可写（未被其他程序占用）。

        若文件不存在，则检查父目录是否可写。
        """
        path = self._get_file_path()
        if not path.exists():
            try:
                test_file = path.parent / ".writable_test"
                test_file.touch()
                test_file.unlink()
                return True
            except (PermissionError, OSError):
                return False
        try:
            with open(path, 'a'):
                pass
            return True
        except (PermissionError, OSError):
            return False

    def _check_and_notify(self):
        """执行一次检测，并在状态变化时触发回调"""
        try:
            writable = self._check_writable()
        except Exception:
            return  # 静默吞掉异常，避免监测线程崩溃

        if self._locked and writable:
            self._locked = False
            self._on_unlocked()
        elif not self._locked and not writable:
            self._locked = True
            self._on_locked()

    def _monitor_loop(self):
        """后台循环：立即检查一次，之后按固定间隔轮询"""
        self._check_and_notify()
        while self._running:
            time.sleep(FILE_MONITOR_INTERVAL)
            self._check_and_notify()
