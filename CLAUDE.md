# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 开发模式运行
python main.py

# 打包为 Windows EXE（版本号自动从 constants.APP_VERSION 读取）
python build.py

# 仅清理上次打包产物
python build.py --clean-only
```

依赖：`flet >= 0.21.0`、`pandas >= 1.3.0`、`pyinstaller >= 3.1`

**终端调试注意事项**：本机终端编码不支持中文字符输出，因此通过 `python -c "..."` 或 `Bash` 运行调试/验证脚本时，所有输出（print、日志、注释）必须使用英文，避免乱码或输出异常。

## Architecture Overview

**Flet 桌面应用**（基于 Flutter 的 Python GUI），从 Excel 人员名单中随机抽取人员。

### 数据流

```
main.py              → 入口：单实例互斥体 → ft.app(target=main)
  ├── config.py       → 路径抽象层：BASE_DIR（可写）/ RESOURCE_DIR（只读）
  ├── constants.py    → 所有颜色、字体、标签、尺寸、限制值（唯一配置源）
  ├── error_handler.py → 全局异常捕获（monkey-patch Flet 事件循环）
  └── RandomSelectorUI → 主界面 + 所有业务逻辑
        ├── PersonnelManager   → pandas Excel 读写 + 选中状态管理
        ├── FileLockMonitor    → 后台线程轮询文件可写入性
        ├── ui_helpers         → DataTable / 菜单项构建器
        └── dialogs            → AlertDialog 工厂函数
```

### 核心设计决策

**路径双轨制** (`config.py`)：
- `BASE_DIR` — 可写数据目录。开发时 = 项目根目录，PyInstaller 打包后 = exe 所在目录
- `RESOURCE_DIR` — 只读资源目录。开发时 = 项目根目录，打包后 = `sys._MEIPASS`（PyInstaller 临时解压目录）
- `bootstrap()` 在首次运行时将资源从 RESOURCE_DIR 复制到 BASE_DIR

**全局异常捕获** (`error_handler.py`)：
Flet 将同步事件处理器（`on_click` 等）通过 `ThreadPoolExecutor` 执行，异常会被 `Future` 吞掉，`sys.excepthook` 无法捕获。解决方案：
1. **主路径**：Monkey-patch `Page.__context_wrapper`（通过 Python name mangling `_Page__context_wrapper`），在用户回调外层包裹 try/except
2. **兜底**：`sys.excepthook` 覆盖，处理事件循环之外的异常（如后台线程）

**文件占用监测** (`file_monitor.py`)：
后台守护线程每 3 秒尝试 `open(path, 'a')` 检测文件是否被 Excel/WPS 锁定。状态变化时通过回调通知 UI 层，锁定状态下拖地模式自动禁用。

**种子系统** (`random_selector_ui.py:81-89`)：
- `seed_enabled=True` → 使用固定种子值，相同种子+相同数据=相同结果
- `seed_enabled=False` → 每次抽选自动生成随机种子并缓存在 `_effective_seed` 中
- 导出结果时种子信息一并写入

**两种抽选模式**：
- **临时模式**：1~20 人（用户输入），不保存状态到文件
- **拖地模式**：固定 3 人，将选中状态写入 Excel。每天仅允许一次，重复点击弹出确认对话框（确认后清除最近 3 条并重抽）

### Excel 数据格式

必须包含列：`姓名`、`学号`、`班级`、`性别`。程序自动维护 `是否已选`（是/否）和 `选择时间` 两列。

### 配置持久化

`config/settings.json`（JSON，通过 `config.py` 的 `load_settings`/`save_settings` 读写）：

| 字段 | 说明 |
|------|------|
| `first_run` | 首次运行标记（`true` 时自动弹出帮助） |
| `data_file` | 当前数据文件路径 |
| `seed_enabled` | 是否启用固定种子 |
| `seed_value` | 种子值 |

### 打包

`build.py` 从 `constants.APP_VERSION` 动态生成 `config/version_info.txt`，通过 PyInstaller `--version-file` 嵌入到 EXE 属性（文件版本、产品名称、版权等）。生成的 `version_info.txt` 已加入 `.gitignore`，只需维护 `constants.py` 中的版本号即可。

### 文件分布（关键文件）

| 文件 | 行数 | 职责 |
|------|------|------|
| `random_selector_ui.py` | ~1150 | 主界面类 `RandomSelectorUI`，包含所有 UI 构建和业务逻辑 |
| `constants.py` | ~100 | 应用级常量：颜色、字体、标签、尺寸、限制值 |
| `config.py` | ~90 | 路径解析、设置读写、首次运行初始化 |
| `error_handler.py` | ~250 | 全局异常捕获 + 日志轮转 + 错误弹窗 |
| `dialogs.py` | ~210 | AlertDialog 工厂：关于、帮助、选项（种子）、确认对话框 |
| `ui_helpers.py` | ~150 | DataTable 构建、菜单项、表格分栏 |
| `file_monitor.py` | ~105 | `FileLockMonitor` 类，后台线程轮询文件可写性 |
| `personnel_manager.py` | ~72 | pandas Excel 读写 + 选中状态 CRUD |
| `main.py` | ~67 | 入口：单实例互斥体 → bootstrap → 启动 Flet app |
| `build.py` | ~167 | PyInstaller 打包脚本，含版本信息自动生成 |