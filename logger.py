"""统一日志模块

基于 Python 标准库 logging，提供按天滚动的文件日志 + 控制台输出。
日志格式: [时间戳] [级别] [模块] 消息

日志分级写入：
- app.log  — INFO 及以上（INFO / WARN / ERROR），日常操作和异常信息
- debug.log — 仅 DEBUG（需在选项中启用），详细调试信息，避免干扰主日志
- stdout   — 所有级别（开发调试用，打包后无控制台无影响）

用法:
    from logger import get_logger
    log = get_logger(__name__)
    log.info("something happened")
    log.debug("detailed debug info")  # 需启用 debug_log 后才写入文件
"""

import logging
import sys

from config import BASE_DIR

# ---------- 常量 ----------

LOG_DIR = BASE_DIR / "config" / "logs"
LOG_FORMAT = "[%(asctime)s.%(msecs)03d] [%(levelname)-5s] [%(module)-8s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 模块名最多显示 8 个字符
_MODULE_MAX_LEN = 8

# 调试日志开关（默认关闭，由 config/settings.json 中的 debug_log_enabled 控制）
_debug_log_enabled = False

# ---------- 过滤器 ----------


class _DebugOnlyFilter(logging.Filter):
    """仅放行 DEBUG 级别的日志记录，过滤掉 INFO 及以上。"""

    def filter(self, record):
        return record.levelno == logging.DEBUG


class _DebugLogGateFilter(logging.Filter):
    """根据 _debug_log_enabled 开关控制是否放行 DEBUG 日志。

    默认不放行（debug.log 为空），用户通过"工具 → 选项"启用后才写入。
    """

    def filter(self, record):
        return _debug_log_enabled


# ---------- 模块名裁剪 Formatter ----------


class _ShortModuleFormatter(logging.Formatter):
    """将模块名裁剪/补齐到固定宽度（8个字符），级别名缩为5个字符"""

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

    from logging.handlers import TimedRotatingFileHandler

    # 主日志 handler：INFO 及以上 → app.log（按天滚动，保留 30 天）
    app_handler = TimedRotatingFileHandler(
        filename=str(LOG_DIR / "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    app_handler.suffix = "%Y-%m-%d"
    app_handler.setFormatter(formatter)
    app_handler.setLevel(logging.INFO)

    # 调试日志 handler：仅 DEBUG → debug.log（按天滚动，保留 30 天）
    debug_handler = TimedRotatingFileHandler(
        filename=str(LOG_DIR / "debug.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    debug_handler.suffix = "%Y-%m-%d"
    debug_handler.setFormatter(formatter)
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.addFilter(_DebugOnlyFilter())
    debug_handler.addFilter(_DebugLogGateFilter())

    # 控制台 handler（仅开发环境有效，打包后无控制台无影响）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    root.addHandler(app_handler)
    root.addHandler(debug_handler)
    root.addHandler(console_handler)


def set_debug_log_enabled(enabled: bool) -> None:
    """设置调试日志开关。

    - True  → DEBUG 日志写入 debug.log
    - False → 不写入任何 DEBUG 日志（默认）

    在"工具 → 选项"中由用户控制。
    """
    global _debug_log_enabled
    _debug_log_enabled = enabled


def is_debug_log_enabled() -> bool:
    """返回调试日志开关的当前状态。"""
    return _debug_log_enabled


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger（便捷函数）。

    Usage:
        from logger import get_logger
        log = get_logger(__name__)
    """
    return logging.getLogger(name)
