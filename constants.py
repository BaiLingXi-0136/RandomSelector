"""应用级常量：颜色、标签、尺寸、限制值等"""

# ==================== 应用元信息 ====================
APP_TITLE = "随机点名系统"
APP_VERSION = "4.4.1"
MUTEX_NAME = r"Local\RandomSelector_v4"

# ==================== 数值限制 ====================
MAX_LOG_FILES = 20            # 错误日志文件最大保留数量
MAX_SELECTION_COUNT = 20
MIN_SELECTION_COUNT = 1
MOPPING_COUNT = 3            # 拖地模式默认选择人数
FILE_MONITOR_INTERVAL = 3    # 文件占用检测间隔（秒）
ANIMATION_DELAY = 0.35       # 逐行动画延迟（秒）
REFRESH_ANIMATION_DURATION = 0.8  # 刷新动画持续时间（秒）
DEFAULT_SEED = 1589564

# ==================== 颜色 ====================
COLOR_PRIMARY = "#4CAF50"
COLOR_DANGER = "#D32F2F"
COLOR_WARNING = "#FF9800"
COLOR_SUCCESS_TEXT = "#2E7D32"
COLOR_HINT = "#666666"
COLOR_SUBTLE = "#888888"
COLOR_BORDER = "#e0e0e0"

COLOR_SUCCESS_BG = "#e8f5e9"
COLOR_ERROR_BG = "#ffebee"
COLOR_WARNING_BG = "#FFF3E0"
COLOR_INFO_BG = "#e3f2fd"
COLOR_LIGHT_BG = "#f5f5f5"
COLOR_NEUTRAL_BG = "#fff8e1"

COLOR_TABLE_HEADER = "#E3F2FD"
COLOR_ROW_HIGHLIGHT = "#FFF9C4"
COLOR_ROW_ALT = "#fff8e1"
COLOR_ROW_SELECTED = "#f1f8e9"

COLOR_LIVE_DISPLAY_TEXT = "#1a1a1a"
COLOR_LIVE_DISPLAY_BG = "#f5f5f5"

COLOR_WARNING_BORDER = "#E65100"

# ==================== 字体 ====================
FONT_FAMILY = "Microsoft YaHei"
FONT_SIZE_TITLE = 24
FONT_SIZE_SECTION = 18
FONT_SIZE_BODY = 14
FONT_SIZE_SMALL = 13
FONT_SIZE_HINT = 12
FONT_SIZE_LIVE = 56       # 实时显示区人名

# ==================== 布局尺寸 ====================
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
BUTTON_WIDTH = 150
BACKTRACK_INPUT_WIDTH = 200
SEED_INPUT_WIDTH = 120
TABLE_COLUMN_SPACING = 12
TABLE_HEADING_ROW_HEIGHT = 38
TABLE_DATA_ROW_MIN_HEIGHT = 32
TABLE_DATA_ROW_MAX_HEIGHT = 40

# ==================== 模式标签 ====================
LABEL_MODE_TEMPORARY = "临时模式（不保存状态）"
LABEL_MODE_MOPPING = "拖地模式（选择3人，保存状态）"
LABEL_MODE_GROUP = "选择模式："

# ==================== 按钮文本 ====================
BTN_START = "开始选择"
BTN_SHOW_ALL = "查看所有人员"
BTN_SHOW_UNSELECTED = "查看未选择人员"
BTN_CLEAR = "清空记录"
BTN_CANCEL = "取消"
BTN_CONFIRM = "确定"
BTN_BACKTRACK = "回溯替换"

# ==================== 菜单文本 ====================
MENU_FILE = "文件"
MENU_EDIT = "编辑"
MENU_VIEW = "视图"
MENU_TOOLS = "工具"
MENU_HELP = "帮助"

# ==================== 提示/警告文本 ====================
WARN_FILE_LOCKED = (
    "文件被占用，无法保存！请关闭其他程序中打开的名单文件后重试。拖地模式已禁用。"
)
WARN_FILE_LOCKED_SELECTION = (
    "文件被占用，无法使用拖地模式！请关闭其他程序中打开的名单文件后重启程序。"
)
WARN_NO_EXPORT_DATA = "没有可导出的抽选结果，请先进行一次选择"
WARN_LOAD_FAILED = "错误：无法加载数据文件"
WARN_EMPTY_LIST = "人员名单为空！"
WARN_ALL_SELECTED = "所有人员都已被选择过！"
HINT_TEMP_NOT_SAVED = "提示：此为临时选择，未保存到原文件"
HINT_BACKTRACK_USAGE = "如选中人员请假或有特殊情况，可输入其学号进行回溯替换"
HINT_SEED = "💡 相同种子 + 相同数据文件 = 相同的抽选结果"

# ==================== 测试/调试 ====================
TEST_ERROR_MESSAGE = "这是一条测试异常，用于验证错误捕获机制是否正常工作。"
