"""统一日志模块

基于 Python 标准库 logging，提供按天滚动的文件日志 + 控制台输出。
日志格式: [时间戳] [级别] [模块] 消息

用法:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("something happened")
"""

import logging
import sys
from pathlib import Path

from config import BASE_DIR

# ---------- 常量 ----------

LOG_DIR = BASE_DIR / "config" / "logs"
LOG_FORMAT = "[%(asctime)s.%(msecs)03d] [%(levelname)-5s] [%(module)-8s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 模块名最多显示 8 个字符
_MODULE_MAX_LEN = 8

# ---------- 模块名裁剪 Formatter ----------


class _ShortModuleFormatter(logging.Formatter):
    """将模块名裁剪/补齐到固定宽度（8字符），级别名缩为5字符"""

    def format(self, record):
        record.module = record.name.split(".")[-1][:_MODULE_MAX_LEN].ljust(_MODULE_MAX_LEN)
        # 统一级别名为 5 字符: INFO / WARN / ERROR
        if record.levelname == "WARNING":
            record.levelname = "WARN "
        elif record.levelname == "CRITICAL":
            record.levelname = "CRIT "
        record.levelname = record.levelname.ljust(5)[:5]
        return super().format(record)


# ---------- 初始化 ----------

_initialized = False


def setup_logging() -> None:
    """初始化日志系统（在 main.py 启动时调用一次）。

    - 按天滚动文件日志，保留 30 天
    - 同时输出到 stdout（开发调试用）
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 避免重复添加 handler（测试等场景）
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    if root.handlers:
        return

    formatter = _ShortModuleFormatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # 文件 handler：按天滚动，保留 30 天
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename=str(LOG_DIR / "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    # 文件名后缀格式: app.log.2026-08-03
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # 控制台 handler（仅开发环境有效，打包后无控制台无影响）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    root.addHandler(file_handler)
    root.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger（便捷函数）。

    Usage:
        from logger import get_logger
        log = get_logger(__name__)
    """
    return logging.getLogger(name)
