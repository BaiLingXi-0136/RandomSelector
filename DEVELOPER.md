# 开发者维护文档

> **目标受众**：本项目开发者 / 维护者。用户手册请参阅 `README.md`。

---

## 目录

1. [项目概览](#1-项目概览)
2. [架构设计](#2-架构设计)
3. [开发环境搭建](#3-开发环境搭建)
4. [模块 API 参考](#4-模块-api-参考)
5. [核心机制深度解析](#5-核心机制深度解析)
6. [编码规范与模式](#6-编码规范与模式)
7. [构建与发布](#7-构建与发布)
8. [调试与故障排查](#8-调试与故障排查)
9. [常见维护任务](#9-常见维护任务)

---

## 1. 项目概览

| 属性     | 说明                                                  |
|--------|-----------------------------------------------------|
| 项目名称   | 随机点名系统 (RandomSelector)                             |
| 当前版本   | `4.4.1`（定义于 `constants.py:5`）                       |
| 技术栈    | Python 3.8+ / Flet (Flutter) / pandas / PyInstaller |
| 目标平台   | Windows 桌面                                          |
| GUI 框架 | Flet ≥ 0.21.0（基于 Flutter 的 Python 绑定）               |
| 数据存储   | Excel `.xlsx`（pandas 读写）                            |
| 配置存储   | JSON (`config/settings.json`)                       |

### 文件清单

```
version4.0/
├── main.py                   # 入口：单实例互斥体 → Flet app 启动
├── config.py                 # 路径抽象层：BASE_DIR / RESOURCE_DIR 双轨制
├── constants.py              # 所有常量：颜色、字体、尺寸、标签、限制值
├── random_selector_ui.py     # 主界面 RandomSelectorUI（~1307 行），UI + 业务逻辑
├── error_handler.py          # 全局异常捕获：monkey-patch + excepthook 兜底
├── dialogs.py                # AlertDialog 工厂函数（关于、帮助、选项、确认）
├── ui_helpers.py             # DataTable / 菜单项 / 分栏表格构建器
├── file_monitor.py           # FileLockMonitor：后台线程轮询文件可写性
├── personnel_manager.py      # PersonnelManager：pandas Excel 读写 + 选中状态 CRUD
├── build.py                  # PyInstaller 打包脚本（版本号自动从 constants 读取）
├── README.md                 # 用户手册
├── CLAUDE.md                 # AI 编码助手指令（非人类开发者文档）
├── DEVELOPER.md              # 本文件
└── config/
    ├── ABOUT.md              # 关于对话框内容（Markdown）
    ├── settings.json          # 运行时配置（JSON）
    ├── icon.ico               # 程序图标
    ├── version_info.txt       # 打包时自动生成，已加入 .gitignore
    └── data/
        ├── DefaultList.xlsx   # 默认人员名单模板
        ├── PersonnelList.xlsx # 实际使用的人员名单（如有）
        └── exports/           # 抽选结果导出目录
```

---

## 2. 架构设计

### 2.1 分层架构

```
┌─────────────────────────────────────────┐
│  main.py         入口 & 单实例保护        │
├─────────────────────────────────────────┤
│  random_selector_ui.py    UI + 业务逻辑   │
│  ├── dialogs.py           对话框工厂      │
│  └── ui_helpers.py        UI 辅助构建     │
├──────────────┬──────────────────────────┤
│ 业务/数据层   │  基础设施层                │
│ ├── personnel │  ├── config.py    路径管理 │
│     _manager  │  ├── constants.py 常量池  │
│ └── file      │  ├── error_handler.py     │
│     _monitor  │  └── build.py    打包脚本  │
└──────────────┴──────────────────────────┘
```

### 2.2 数据流

```
用户操作（点击按钮/菜单）
    │
    ▼
RandomSelectorUI (事件处理器)
    │
    ├──► PersonnelManager.load_data()    ←── pandas.read_excel()
    ├──► random.sample(random_state=...) ←── 种子系统控制可复现性
    ├──► PersonnelManager.save_data()    ←── pandas.to_excel()
    ├──► dialogs.show_xxx_dialog()       ←── 弹窗确认
    └──► ui_helpers.build_xxx_table()    ←── 构建 DataTable
    │
    ▼
Flet Page 渲染 & 更新
```

### 2.3 路径双轨制（`config.py`）

这是项目最核心的基础设施设计决策，支撑"开发→打包"无缝切换：

| 环境                        | `BASE_DIR`（可写） | `RESOURCE_DIR`（只读）                 |
|---------------------------|----------------|------------------------------------|
| 开发 (`python main.py`)     | 项目根目录          | 项目根目录（同 BASE_DIR）                  |
| 打包 (`RandomSelector.exe`) | exe 所在目录       | `sys._MEIPASS`（PyInstaller 临时解压目录） |

**规则**：
- 所有**需要写入**的路径（配置文件、数据文件、日志、导出）→ 使用 `BASE_DIR`
- 所有**只读资源**（图标、ABOUT.md、默认模板）→ 使用 `RESOURCE_DIR`
- `bootstrap()` 在首次运行时将只读资源复制到可写目录

**新增资源文件时**，需要：
1. 在 `config.py` 的 `bootstrap()` 中添加 `_copy_if_missing()` 调用
2. 在 `build.py` 的 `DATAS` 列表中添加 `(源路径, 目标目录)` 元组

### 2.4 单实例保护（`main.py:14-29`）

通过 Windows 命名互斥体（Named Mutex）实现：

```
CreateMutexW("Local\RandomSelector_v4")  →  ERROR_ALREADY_EXISTS (183)  →  sys.exit(0)
```

- 互斥体名称为 `constants.MUTEX_NAME`
- 句柄保存在全局变量 `_mutex_handle` 防止 GC 回收
- 仅 Windows 平台有效（通过 `ctypes.windll.kernel32` 调用）

---

## 3. 开发环境搭建

### 3.1 基本要求

```bash
# Python 3.8+
python --version

# 安装依赖
pip install flet>=0.21.0 pandas>=1.3.0

# 安装打包工具（仅构建时）
pip install pyinstaller>=3.1
```

### 3.2 运行开发模式

```bash
python main.py
```

### 3.3 目录初始化行为

首次运行流程：
1. `main()` → `bootstrap()`
2. 创建 `config/`、`config/data/` 目录
3. 复制 `ABOUT.md`、`DefaultList.xlsx` 到 `config/`
4. 加载 `settings.json`（不存在则使用默认值）
5. `first_run == true` → 自动弹出帮助对话框

### 3.4 调试建议

- **终端编码**：本机终端不支持中文，调试脚本使用英文输出
- **错误日志**：`config/logs/error_*.log` 包含完整 Traceback
- **测试异常捕获**：菜单 → 工具 → 测试错误捕获，验证异常处理链正常

---

## 4. 模块 API 参考

### 4.1 `config.py` — 路径管理与配置持久化

```python
# 路径常量
BASE_DIR: Path         # 可写数据根目录
RESOURCE_DIR: Path     # 只读资源根目录
CONFIG_DIR: Path       # BASE_DIR / "config"
DATA_DIR: Path         # CONFIG_DIR / "data"
DEFAULT_EXCEL_FILE: Path  # DATA_DIR / "DefaultList.xlsx"
SETTINGS_FILE: Path    # CONFIG_DIR / "settings.json"

# 函数
bootstrap()                              # 首次运行初始化（复制资源文件）
load_settings() -> dict                  # 读取 settings.json，失败返回 {}
save_settings(settings: dict) -> None    # 合并写入 settings.json
get_data_file_path() -> Path             # 从设置获取数据文件路径，无效返回默认
```

**添加新配置字段**：
1. 在 `constants.py` 定义默认值
2. 在 `load_settings()` 调用处提供默认值
3. 在 `save_settings()` 调用处确保字段被传入

### 4.2 `constants.py` — 常量池

所有"魔数"的唯一定义位置。修改 UI 外观或行为时优先改这里。

**分类**：

| 分类    | 前缀/说明                                            | 示例                                |
|-------|--------------------------------------------------|-----------------------------------|
| 应用元信息 | `APP_*`, `MUTEX_NAME`                            | `APP_VERSION = "4.4.1"`           |
| 数值限制  | `MAX_*`, `MIN_*`, `*_COUNT`                      | `MAX_SELECTION_COUNT = 20`        |
| 颜色    | `COLOR_*`（Hex 字符串）                               | `COLOR_PRIMARY = "#4CAF50"`       |
| 字体    | `FONT_*`                                         | `FONT_FAMILY = "Microsoft YaHei"` |
| 布局尺寸  | `*_WIDTH`, `*_HEIGHT`, `*_SPACING`               | `WINDOW_WIDTH = 800`              |
| 文本标签  | `LABEL_*`, `BTN_*`, `MENU_*`, `WARN_*`, `HINT_*` | `BTN_START = "开始选择"`              |
| 测试    | `TEST_*`                                         | `TEST_ERROR_MESSAGE`              |

### 4.3 `personnel_manager.py` — 数据层

```python
class PersonnelManager:
    df: pd.DataFrame | None          # 当前加载的数据
    file_path: Path                   # 当前数据文件路径
    file_name: str                    # 文件名（只读属性）

    def set_file_path(path)           # 切换数据文件，同时持久化到 settings
    def load_data() -> bool           # 从 Excel 加载，自动补全'是否已选'/'选择时间'列
    def get_all_personnel() -> DataFrame   # 返回副本
    def get_unselected_personnel() -> DataFrame  # '是否已选' == '否'
    def update_selection_status(indices, selected=True)  # 批量更新选中状态+时间戳
    def save_data()                   # 写入 Excel（可能因文件被占用抛异常）
    def clear_selection_records()     # 重置所有'是否已选'为'否'
```

**Excel 数据格式要求**：
- 必须有列：`姓名`、`学号`、`班级`、`性别`
- 程序自动维护列：`是否已选`（是/否）、`选择时间`（datetime 字符串）

### 4.4 `random_selector_ui.py` — UI 层

```python
class RandomSelectorUI:
    """主界面控制器，约 1307 行。所有 UI 构建和业务逻辑在此。"""

    # === 生命周期 ===
    def build_main_view() -> ft.Column    # 构建完整主界面，返回顶层 Column
    def setup_file_monitor()              # 在 main() 末尾调用，启动文件监测线程

    # === 核心业务 ===
    def start_selection(e)                # "开始选择"按钮回调
    def display_selection_result(rows, title, saved, animate, highlight_name)
    def clear_records()                   # 清空所有选中记录
    def show_all_personnel(e)             # 展示全量人员表格
    def show_unselected_personnel(e)      # 展示未选人员表格

    # === 回溯系统 ===
    def _do_backtrack(e)                  # 回溯替换主逻辑
    def _filter_out_backtracked(df)       # 从池中排除本轮已被回溯的人员

    # === 种子系统 ===
    @property _random_state -> int        # 获取本次抽选种子（自动生成或固定值）
    _seed_enabled: bool                   # 是否启用固定种子
    _seed_value: int                      # 固定种子值
    _effective_seed: int | None           # 本次抽选实际使用的种子（缓存）
```

### 4.5 `error_handler.py` — 全局异常捕获

```python
def setup_error_handler(page: ft.Page)   # 注册异常钩子（在 main 中尽早调用）

# 内部机制：
# 1. _patch_flet_handler(page)  → monkey-patch Page._Page__context_wrapper
# 2. sys.excepthook = _exception_hook  → 兜底捕获
# 异常时 → _write_exception_log() 写入日志 → _show_error_dialog() 弹窗
```

**日志位置**：`config/logs/error_YYYYMMDD_HHMMSS.log`
**日志轮转**：最多保留 `MAX_LOG_FILES`（默认 20）个文件

### 4.6 `dialogs.py` — 对话框工厂

```python
# 关于/帮助
show_about_dialog(page)              # 从 ABOUT.md 读取内容
open_help_dialog(page)               # 从 README.md 读取内容
on_menu_about(e)                     # 菜单事件桥接
on_menu_help(e)                      # 菜单事件桥接

# 配置
show_options_dialog(page, seed_enabled, seed_value, on_save)

# 通用确认
show_confirm_dialog(page, title, content, confirm_label, on_confirm, on_cancel=None)
show_clear_records_confirm(page, on_confirm)    # 清空记录确认
show_mopping_redo_confirm(page, on_confirm)     # 拖地重抽确认
```

### 4.7 `ui_helpers.py` — UI 辅助

```python
# 工具函数
safe_val(val) -> str                          # NaN → ""

# 菜单
menu_item(label, shortcut, icon, on_click, disabled) -> ft.MenuItemButton

# 表格
make_selection_table() -> ft.DataTable         # 空表（5列：序号/姓名/学号/班级/性别）
make_row_cells(i, row) -> list[ft.DataCell]    # 一行 DataCell
build_personnel_table(df, include_status, start_index) -> ft.DataTable
build_split_personnel_tables(df, include_status) -> ft.Row  # 左右分栏
```

### 4.8 `file_monitor.py` — 文件占用监测

```python
class FileLockMonitor:
    is_locked: bool           # 当前是否被锁定（只读属性）

    def __init__(get_file_path, on_locked, on_unlocked)
    def start()               # 启动后台守护线程（daemon=True）
    def stop()                # 停止监测

    # 内部：每 FILE_MONITOR_INTERVAL 秒尝试 open(path, 'a')
```

### 4.9 `build.py` — 打包脚本

```bash
python build.py              # 清理 + 打包
python build.py --clean-only # 仅清理
```

**打包流程**：
1. `generate_version_file()` — 从 `constants.APP_VERSION` 动态生成 `config/version_info.txt`
2. `clean()` — 删除 `build/`、`dist/`、`*.spec`、`version_info.txt`
3. `build()` — 调用 PyInstaller，`--windowed` 模式
4. 复制 `README.md` 到 `dist/RandomSelector/`

---

## 5. 核心机制深度解析

### 5.1 种子系统

**目的**：相同种子 + 相同数据 = 相同抽选结果（可复现性）。

**实现**（`random_selector_ui.py:81-91`）：
```python
@property
def _random_state(self) -> int:
    if self._effective_seed is None:
        if self._seed_enabled:
            self._effective_seed = self._seed_value      # 固定种子
        else:
            self._effective_seed = random.randint(1, 2**31 - 1)  # 随机种子
    return self._effective_seed
```

**关键行为**：
- `start_selection()` 中重置 `_effective_seed = None`，确保每次抽选独立
- `_random_state` 被惰性求值，首次访问时确定种子并缓存
- `pandas.DataFrame.sample(random_state=self._random_state)` 使用该种子
- 导出结果时种子值一并写入文件
- 回溯替换中每次替换后重置 `_effective_seed = None`，使下次回溯产生不同结果

**配置持久化**：`settings.json` 中的 `seed_enabled` 和 `seed_value` 字段。

### 5.2 回溯替换机制

**目的**：选中人员请假/缺席时，替换为另一人。

**完整流程**（`random_selector_ui.py:925-999`）：

```
用户输入学号
  │
  ├─► _on_backtrack_input_change()    ← 实时校验（绿色=找到，红色=不在列表中）
  │
  └─► 点击"回溯替换" → _do_backtrack()
        │
        ├─► 1. 校验输入（非空、在选中列表中）
        ├─► 2. 记录被替换者学号到 _backtracked_ids（本轮排除）
        ├─► 3. 构建候选池：
        │      临时模式: all_personnel - remaining - backtracked_ids
        │      拖地模式: unselected - remaining - backtracked_ids
        ├─► 4. 从候选池中随机选 1 人（独立种子）
        ├─► 5. 拖地模式: 更新 Excel（撤销旧选中 + 标记新选中）
        ├─► 6. 重建 _last_selected_rows（保持原顺序，替换指定位置）
        └─► 7. 重新渲染结果 + 回溯面板
```

**防重复机制**：
- `_backtracked_ids` 集合记录本轮所有被回溯剔除的人员学号
- `_filter_out_backtracked()` 从候选池中排除这些人员
- `start_selection()` 中清空 `_backtracked_ids`（新一轮开始）

### 5.3 文件占用监测

**目的**：检测 Excel 文件是否被 Excel/WPS 等外部程序锁定。

**实现**（`file_monitor.py`）：
- 后台守护线程每 `FILE_MONITOR_INTERVAL`（3秒）执行 `open(path, 'a')`
- 状态变化时触发回调：
  - 锁定 → `_handle_file_locked()`：显示橙色警告栏 + 禁用拖地模式 + 强制切回临时模式
  - 解锁 → `_handle_file_unlocked()`：隐藏警告 + 恢复拖地模式

**线程安全**：
- `_locked` 状态由监测线程写入、UI 线程读取（bool 赋值在 CPython 中是原子操作）
- 回调在监测线程中执行（需确保 Flet 控件更新的线程安全性）

### 5.4 拖地模式每日限制

**实现**（`random_selector_ui.py:691-699`）：
```python
def _has_today_selection(self) -> bool:
    today_str = datetime.now().strftime('%Y-%m-%d')
    mask = (df['是否已选'] == '是') & (
        df['选择时间'].astype(str).str.startswith(today_str)
    )
    return mask.any()
```

- 检查 `选择时间` 列是否有当天日期的记录
- 如果存在 → 弹出确认对话框（确认后清除最近 3 条重抽）
- 重抽逻辑：`_do_mopping_redo()` 中按时间倒序取最近 3 条 → 取消选中 → 重新抽取

### 5.5 全局异常捕获

**问题背景**：Flet 将同步事件处理器通过 `ThreadPoolExecutor` 执行，异常被 `Future` 吞掉，`sys.excepthook` 无法捕获。

**解决方案**（双重保障）：

```
主路径（monkey-patch）
  Page._Page__context_wrapper
    → _patched_wrapper → try/except → _handle_flet_exception()
                                                   ├── _write_exception_log() → config/logs/
                                                   └── _show_error_dialog()  → ft.AlertDialog

兜底（excepthook）
  sys.excepthook = _exception_hook  → 同上处理 → 调用原始 excepthook
```

**Flet 版本兼容性**：
- 使用 Python name mangling `_Page__context_wrapper` 访问私有属性
- 若未来版本变更导致 `AttributeError`，静默降级（至少 excepthook 仍生效）

### 5.6 结果显示动画

**实现**（`random_selector_ui.py:1014-1050`）：
- 逐行添加 `DataRow`，每行间隔 `ANIMATION_DELAY`（0.35秒）
- 当前行高亮（`COLOR_ROW_HIGHLIGHT`），上一行恢复交替色
- 顶部大字体实时显示当前抽取姓名（56px）
- 动画期间禁用所有按钮（`_set_buttons_disabled(True)`）
- `finally` 块确保按钮恢复可用
- ≤2 人时单表显示，>2 人时分左右两栏

---

## 6. 编码规范与模式

### 6.1 总体原则

- **常量集中管理**：所有颜色/字号/尺寸/标签文本均在 `constants.py` 定义，其他地方禁止硬编码
- **UI 与业务逻辑共处**：当前架构下 `RandomSelectorUI` 同时承载 UI 构建和业务逻辑，不做严格 MVVM 分离（保持简单）
- **对话框独立工厂**：AlertDialog 创建集中在 `dialogs.py`，UI 主文件只调用工厂函数
- **防御性编程**：所有文件 I/O、JSON 解析均包裹 try/except，失败时静默降级

### 6.2 命名约定

| 类型        | 约定                       | 示例                                       |
|-----------|--------------------------|------------------------------------------|
| 模块        | `snake_case`             | `personnel_manager.py`                   |
| 类         | `PascalCase`             | `RandomSelectorUI`、`FileLockMonitor`     |
| 公开方法      | `snake_case`             | `start_selection()`、`load_data()`        |
| 私有方法      | `_leading_underscore`    | `_do_mopping_selection()`                |
| 常量        | `UPPER_SNAKE`            | `MAX_SELECTION_COUNT`                    |
| 控件属性      | `snake_case`             | `self.btn_start`、`self._backtrack_input` |
| Flet 控件引用 | `self.xxx` 存于 `__init__` | 可空类型用 `\| None`                          |

### 6.3 模式：Flet 事件处理器签名

```python
# 所有事件处理器接收一个 event 参数（即使不用）
def handler(self, e):         # _e 表示未使用
    page = e.page             # 从 event 获取 page 引用
    control = e.control       # 获取触发事件的控件
```

### 6.4 模式：Flet 控件更新

```python
# 更新控件前务必检查 page 是否已挂载
if self.some_control is not None and self.some_control.page is not None:
    self.some_control.value = "new value"
    self.some_control.update()

# page.update() 刷新整个页面（开销较大，仅在需要时使用）
e.page.update()
```

### 6.5 模式：错误/成功消息容器

```python
# 错误消息：红色背景的 Container
ft.Container(
    ft.Text(message, color="#B71C1C", weight=ft.FontWeight.BOLD),
    bgcolor=COLOR_ERROR_BG,     # "#ffebee"
    padding=10,
    border_radius=5,
)

# 成功消息：绿色背景的 Container
ft.Container(
    ft.Text(message, weight=ft.FontWeight.BOLD),
    bgcolor=COLOR_SUCCESS_BG,   # "#e8f5e9"
    padding=10,
    border_radius=5,
)
```

先在 `_remove_result_errors()` 中清除旧消息，再插入新消息到 `result_area.controls` 顶部。

### 6.6 模式：添加新菜单项

```python
# 1. 在 constants.py 添加标签常量（如需要）
MENU_NEW_FEATURE = "新功能"

# 2. 在 random_selector_ui.py 的 _build_menu_bar() 中添加 SubmenuButton/MenuItemButton
menu_item("新功能", "",
          icon=ft.Icon(ft.Icons.STAR),
          on_click=self._on_new_feature),

# 3. 实现事件处理器方法
def _on_new_feature(self, e):
    ...
```

### 6.7 类型注解

项目使用 Python 3.10+ 风格的类型注解：
```python
path: Path | None = None
def func() -> tuple[bool, str | None]: ...
```

---

## 7. 构建与发布

### 7.1 版本号管理

**唯一版本源**：`constants.py:5` → `APP_VERSION = "4.4.1"`

**版本号同步路径**：
```
constants.APP_VERSION
  ├── build.py → generate_version_file() → version_info.txt → 嵌入 EXE 属性
  └── main.py → page.title (窗口标题)
```

**发版步骤**：
1. 更新 `constants.py` 中的 `APP_VERSION`
2. 更新 `config/ABOUT.md` 中的版本号和日期
3. 更新 `CHANGELOG.md`
4. 提交变更：`git commit -m "chore: bump version to X.Y.Z"`
5. 打标签：`git tag vX.Y.Z`
6. 运行 `python build.py` 打包

### 7.2 PyInstaller 打包

```bash
python build.py
```

**产物结构**：
```
dist/RandomSelector/
├── RandomSelector.exe       # 主程序（--windowed 无控制台窗口）
├── README.md                # 帮助文档（build.py 自动复制）
├── _internal/               # PyInstaller 运行时依赖
└── config/                  # 用户目录（首次运行时自动创建）
```

**新增打包资源**时，修改 `build.py` 的 `DATAS` 列表：
```python
DATAS = [
    ("config/icon.ico", "config"),
    ("config/ABOUT.md", "config"),
    ("config/data/DefaultList.xlsx", "config/data"),
    ("path/to/new_file", "target_dir"),  # 新增
]
```

### 7.3 生成 version_info.txt

`build.py:generate_version_file()` 负责将 `APP_VERSION` 字符串解析为 4 段版本元组：
- `"4.3"` → `(4, 3, 0, 0)`
- `"4.4.1"` → `(4, 4, 1, 0)`

该文件已加入 `.gitignore`，不要手动编辑。

---

## 8. 调试与故障排查

### 8.1 常见问题

| 问题                  | 原因                   | 解决方案                                        |
|---------------------|----------------------|---------------------------------------------|
| `WARN_LOAD_FAILED`  | Excel 文件不存在或格式不正确    | 确认文件路径有效，包含必需列 `姓名/学号/班级/性别`                |
| 文件被占用，拖地模式禁用        | Excel/WPS 打开了数据文件    | 关闭外部程序中打开的文件，程序自动恢复                         |
| `WARN_ALL_SELECTED` | 所有人员都已被标记为"已选"       | 使用"清空选择记录"重置状态                              |
| 打包后程序闪退             | 缺少资源文件或 DLL          | 检查 `build.py` 的 `DATAS` 配置；查看 `error_*.log` |
| 回溯替换选了同一个人          | 候选池为空                | 已被 `_filter_out_backtracked()` 保护，正常情况下不会发生 |
| 终端中文乱码              | Git Bash 编码问题        | 使用英文输出调试信息                                  |
| 动画期间界面无响应           | `time.sleep()` 阻塞主线程 | 这是已知限制，动画通常 < 10 秒，可接受                      |

### 8.2 错误日志分析

```
config/logs/error_20260712_143025.log

错误发生时间：2026-07-12 14:30:25
══════════════════════════════════════════════

Traceback (most recent call last):
  File "...", line XX, in ...
ExceptionType: 具体原因

══════════════════════════════════════════════
```

### 8.3 验证异常捕获是否正常

- 菜单 → **工具 → 测试错误捕获**
- 应弹出错误对话框，显示 `RuntimeError` 及 Traceback
- 同时在 `config/logs/` 生成日志文件
- 此测试在 `_build_menu_bar()` 中使用 `(_ for _ in ()).throw(RuntimeError(...))` 触发

### 8.4 Flet 页面调试

```python
# 在事件处理器中打印页面结构
print(page.controls)

# 查看控件属性
print(dir(some_control))

# Flet 版本
import flet as ft
print(ft.__version__)
```

---

## 9. 常见维护任务

### 9.1 修改默认抽选人数范围

编辑 `constants.py`：
```python
MAX_SELECTION_COUNT = 20   # 改为需要的上限
MIN_SELECTION_COUNT = 1    # 改为需要的下限
MOPPING_COUNT = 3          # 拖地模式固定人数
```

### 9.2 修改 UI 主题色

编辑 `constants.py` 中的 `COLOR_*` 常量。所有颜色均为 Hex 字符串（如 `"#4CAF50"`）。

### 9.3 添加新的 Excel 数据列要求

1. 在 `personnel_manager.py` 的 `load_data()` 中添加列存在性检查和自动创建
2. 在 `ui_helpers.py` 的 `build_personnel_table()` 中添加新列
3. 在 `make_row_cells()` 中添加新列
4. 如需在导出中包含，修改 `_on_export_results()`

### 9.4 添加新的配置项

1. 在 `constants.py` 定义默认值（如需要）
2. 在 `config.py` 的 `load_settings()` 调用处添加 `.get("new_key", default)`
3. 在相应组件中读写新字段
4. 更新 README.md 的配置说明表格

### 9.5 升级 Flet 版本

1. 阅读 [Flet 更新日志](https://flet.dev/docs/release-notes) 了解破坏性变更
2. 检查 `error_handler.py` 中的 monkey-patch 是否仍然兼容（`_Page__context_wrapper` 属性名可能变化）
3. 全面测试所有 UI 交互（尤其嵌套滚动容器、动画、表格渲染）
4. 更新 CLAUDE.md 和本文件中的版本要求

### 9.6 更换程序图标

1. 替换 `config/icon.ico` 文件
2. 重新打包（`build.py` 通过 `--icon` 参数引用图标）

### 9.7 Git 工作流

```bash
# 当前分支策略：master 主分支
git checkout -b feature/xxx    # 创建功能分支
# ... 开发 ...
git add .
git commit -m "feat: 简要描述"
git checkout master
git merge feature/xxx
git branch -d feature/xxx
```

---

> **最后更新**：2026-07-12
