"""随机点名系统 — UI 层"""
import time
import pandas as pd
import flet as ft
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, load_settings, save_settings
from constants import (
    APP_TITLE, BUTTON_WIDTH, COLOR_DANGER, COLOR_PRIMARY, COLOR_WARNING,
    COLOR_BORDER, COLOR_ERROR_BG, COLOR_HINT, COLOR_INFO_BG, COLOR_LIGHT_BG,
    COLOR_NEUTRAL_BG, COLOR_ROW_ALT, COLOR_ROW_HIGHLIGHT, COLOR_SUCCESS_BG,
    COLOR_SUCCESS_TEXT,
    COLOR_SUBTLE, COLOR_WARNING_BG, COLOR_WARNING_BORDER,
    FONT_SIZE_BODY, FONT_SIZE_HINT, FONT_SIZE_LIVE, FONT_SIZE_SECTION, FONT_SIZE_SMALL,
    FONT_SIZE_TITLE, LABEL_MODE_GROUP, LABEL_MODE_MOPPING, LABEL_MODE_TEMPORARY,
    MAX_SELECTION_COUNT, MIN_SELECTION_COUNT, MOPPING_COUNT,
    BACKTRACK_INPUT_WIDTH, ANIMATION_DELAY,
    BTN_START, BTN_SHOW_ALL, BTN_SHOW_UNSELECTED, BTN_CLEAR, BTN_BACKTRACK,
    MENU_FILE, MENU_EDIT, MENU_VIEW, MENU_TOOLS, MENU_HELP,
    WARN_FILE_LOCKED, WARN_FILE_LOCKED_SELECTION,
    WARN_LOAD_FAILED, WARN_EMPTY_LIST, WARN_ALL_SELECTED, WARN_NO_EXPORT_DATA,
    HINT_TEMP_NOT_SAVED, HINT_BACKTRACK_USAGE,
)
from dialogs import (
    on_menu_about, on_menu_help,
    show_options_dialog, show_clear_records_confirm, show_mopping_redo_confirm,
)
from file_monitor import FileLockMonitor
from personnel_manager import PersonnelManager
from ui_helpers import (
    safe_val, make_selection_table, make_row_cells,
    build_split_personnel_tables, menu_item,
)


class RandomSelectorUI:
    """随机点名系统主界面"""

    def __init__(self):
        self.personnel_manager = PersonnelManager()
        self.result_area: ft.Column | None = None
        self.current_mode = "temporary"
        self.mode_group: ft.RadioGroup | None = None
        self.temp_count_input: ft.TextField | None = None
        self.temp_input_container: ft.Column | None = None
        self.btn_start: ft.ElevatedButton | None = None
        self.btn_show_all: ft.ElevatedButton | None = None
        self.btn_show_unselected: ft.ElevatedButton | None = None
        self.btn_clear: ft.ElevatedButton | None = None
        self.main_column: ft.Column | None = None

        # 回溯功能
        self._last_selected_rows: pd.DataFrame | None = None
        self._last_mode: str | None = None
        self._backtrack_input: ft.TextField | None = None
        self._btn_backtrack: ft.ElevatedButton | None = None
        self._backtrack_error: ft.Text | None = None
        self._temp_count_error: ft.Text | None = None

        # 文件占用
        self._mopping_radio: ft.Radio | None = None
        self._file_lock_warning: ft.Container | None = None
        self._file_monitor: FileLockMonitor | None = None

        # 状态与菜单
        self.status_text: ft.Text | None = None
        self.menu_bar: ft.MenuBar | None = None
        self.file_picker: ft.FilePicker | None = None

        # 种子设置
        settings = load_settings()
        self._seed_enabled: bool = settings.get("seed_enabled", False)
        self._seed_value: int = settings.get("seed_value", 42)

    # ==================== 辅助属性 ====================

    @property
    def _random_state(self) -> int | None:
        return self._seed_value if self._seed_enabled else None

    @property
    def _is_file_locked(self) -> bool:
        if self._file_monitor is not None:
            return self._file_monitor.is_locked
        return False

    # ==================== 状态栏 ====================

    def _refresh_status(self):
        if self.status_text is None:
            return
        if self.personnel_manager.load_data():
            df = self.personnel_manager.df
            total = len(df)
            selected = (df['是否已选'] == '是').sum()
            unselected = total - selected
            self.status_text.value = (
                f"当前文件：{self.personnel_manager.file_name}　|　"
                f"共 {total} 人，已选 {selected} 人，未选 {unselected} 人"
            )
        else:
            self.status_text.value = f"未能加载数据文件：{self.personnel_manager.file_name}"
        if self.status_text.page is not None:
            self.status_text.update()

    # ==================== 菜单栏 ====================

    def _build_menu_bar(self):
        self.menu_bar = ft.MenuBar(
            expand=True,
            controls=[
                ft.SubmenuButton(
                    content=ft.Text(MENU_FILE),
                    controls=[
                        menu_item("打开数据文件...", "",
                                  icon=ft.Icon(ft.Icons.FOLDER_OPEN),
                                  on_click=self._on_open_file_click),
                        ft.MenuItemButton(),
                        menu_item("退出", "",
                                  icon=ft.Icon(ft.Icons.EXIT_TO_APP),
                                  on_click=lambda e: e.page.window.close()),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text(MENU_EDIT),
                    controls=[
                        menu_item("清空选择记录...", "",
                                  icon=ft.Icon(ft.Icons.CLEAR_ALL),
                                  on_click=self._on_clear_records_menu),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text(MENU_VIEW),
                    controls=[
                        menu_item("查看所有人员", "",
                                  icon=ft.Icon(ft.Icons.PEOPLE),
                                  on_click=self._on_show_all_menu),
                        menu_item("查看未选择人员", "",
                                  icon=ft.Icon(ft.Icons.PERSON_OUTLINE),
                                  on_click=self._on_show_unselected_menu),
                        ft.MenuItemButton(),
                        menu_item("刷新", "",
                                  icon=ft.Icon(ft.Icons.REFRESH),
                                  on_click=lambda _: self._refresh_status()),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text(MENU_TOOLS),
                    controls=[
                        menu_item("导出结果...", "",
                                  icon=ft.Icon(ft.Icons.SAVE_ALT),
                                  on_click=self._on_export_results),
                        ft.MenuItemButton(),
                        menu_item("选项...", "",
                                  icon=ft.Icon(ft.Icons.SETTINGS),
                                  on_click=self._on_options_click),
                    ],
                ),
                ft.SubmenuButton(
                    content=ft.Text(MENU_HELP),
                    controls=[
                        menu_item("使用说明", "",
                                  icon=ft.Icon(ft.Icons.HELP_OUTLINE),
                                  on_click=on_menu_help),
                        ft.MenuItemButton(),
                        menu_item("关于...", "",
                                  icon=ft.Icon(ft.Icons.INFO_OUTLINE),
                                  on_click=on_menu_about),
                    ],
                ),
            ],
        )
        return self.menu_bar

    # ---- 菜单事件桥接 ----

    def _on_open_file_click(self, _e):
        if self.file_picker is not None:
            self.file_picker.pick_files(
                allowed_extensions=["xlsx"],
                dialog_title="选择人员数据文件",
                file_type=ft.FilePickerFileType.CUSTOM,
            )

    def _on_clear_records_menu(self, e):
        show_clear_records_confirm(e.page, on_confirm=lambda: self.clear_records())

    def _on_show_all_menu(self, e):
        if self.btn_show_all is not None:
            self.show_all_personnel(e)

    def _on_show_unselected_menu(self, e):
        if self.btn_show_unselected is not None:
            self.show_unselected_personnel(e)

    # ==================== 选项对话框 ====================

    def _on_options_click(self, e):
        show_options_dialog(
            page=e.page,
            seed_enabled=self._seed_enabled,
            seed_value=self._seed_value,
            on_save=self._save_seed_settings,
        )

    def _save_seed_settings(self, enabled: bool, value: int):
        self._seed_enabled = enabled
        self._seed_value = value
        save_settings({
            "seed_enabled": enabled,
            "seed_value": value,
        })

    # ==================== 导出结果 ====================

    def _on_export_results(self, _e):
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            self._show_result_error(WARN_NO_EXPORT_DATA)
            return

        export_dir = DATA_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"抽选结果_{timestamp}.txt"
        file_path = export_dir / file_name

        mode_label = "拖地模式" if self._last_mode == "mopping" else "临时模式"
        lines = [
            "=" * 40,
            f"{APP_TITLE} - 抽选结果",
            "=" * 40,
            "",
            f"导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"抽选模式：{mode_label}",
            f"选中人数：{len(self._last_selected_rows)}",
            "",
            "-" * 40,
            "选中人员列表",
            "-" * 40,
            "",
        ]
        for i, (_, row) in enumerate(self._last_selected_rows.iterrows(), 1):
            lines.append(
                f"{i:>3}. {safe_val(row['姓名'])}  "
                f"学号：{safe_val(row['学号'])}  "
                f"班级：{safe_val(row['班级'])}  "
                f"性别：{safe_val(row['性别'])}"
            )
        lines.extend(["", "=" * 40])

        try:
            file_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            self._show_result_error(f"导出失败：无法写入文件 {file_name}")
            return

        self._remove_result_errors()
        self.result_area.controls.insert(
            0,
            ft.Container(
                ft.Text(
                    f"导出成功！文件已保存至：config/data/exports/{file_name}",
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor=COLOR_SUCCESS_BG,
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=10, left=0, right=0),
            ),
        )
        self.result_area.update()

    # ==================== 错误提示 ====================

    def _show_result_error(self, message: str):
        self._remove_result_errors()
        self.result_area.controls.insert(
            0,
            ft.Container(
                ft.Text(message, color="#B71C1C", weight=ft.FontWeight.BOLD),
                bgcolor=COLOR_ERROR_BG,
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=10, left=0, right=0),
            ),
        )
        self.result_area.update()

    def _remove_result_errors(self):
        to_remove = [
            c for c in self.result_area.controls
            if isinstance(c, ft.Container) and getattr(c, 'bgcolor', None) == COLOR_ERROR_BG
        ]
        for c in to_remove:
            self.result_area.controls.remove(c)

    # ==================== 文件选择回调 ====================

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        if e.files is None or len(e.files) == 0:
            return

        new_path = Path(e.files[0].path)
        self.personnel_manager.set_file_path(new_path)

        self.result_area.controls.clear()
        self.result_area.controls.append(
            ft.Container(
                ft.Text(f"已切换数据文件：{new_path.name}", weight=ft.FontWeight.BOLD),
                bgcolor=COLOR_SUCCESS_BG,
                padding=10,
                border_radius=5,
            )
        )
        self.result_area.update()

        self._clear_selection_context()
        self._refresh_status()

    # ==================== 主界面构建 ====================

    def build_main_view(self):
        self.result_area = ft.Column([])
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self._build_menu_bar()

        # 模式选择
        self._mopping_radio = ft.Radio(label=LABEL_MODE_MOPPING, value="mopping")
        self.mode_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(label=LABEL_MODE_TEMPORARY, value="temporary"),
                self._mopping_radio,
            ]),
            value="temporary",
            on_change=self.on_mode_change,
        )

        self.btn_clear = ft.ElevatedButton(
            BTN_CLEAR,
            on_click=lambda e: show_clear_records_confirm(
                e.page, on_confirm=lambda: self.clear_records()
            ),
            style=ft.ButtonStyle(bgcolor="#f44336", color="white"),
            width=BUTTON_WIDTH,
        )

        mode_control = ft.Column([
            ft.Text(LABEL_MODE_GROUP, weight=ft.FontWeight.BOLD),
            self.mode_group,
            self.btn_clear,
        ])

        # 临时模式人数输入
        self.temp_count_input = ft.TextField(
            label="选择人数",
            value="1",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            visible=True,
            on_change=self._on_temp_count_change,
            border_color=COLOR_PRIMARY,
        )
        self._temp_count_error = ft.Text("", size=12, color=COLOR_DANGER, visible=False)

        self.temp_input_container = ft.Column([
            ft.Row([
                ft.Text("选择人数："),
                self.temp_count_input,
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([
                self._temp_count_error,
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], visible=True)

        # 按钮区域
        self.btn_start = ft.ElevatedButton(
            BTN_START,
            on_click=self.start_selection,
            style=ft.ButtonStyle(bgcolor=COLOR_PRIMARY, color="white"),
            width=BUTTON_WIDTH,
        )
        self.btn_show_all = ft.ElevatedButton(
            BTN_SHOW_ALL,
            on_click=self.show_all_personnel,
            width=BUTTON_WIDTH,
        )
        self.btn_show_unselected = ft.ElevatedButton(
            BTN_SHOW_UNSELECTED,
            on_click=self.show_unselected_personnel,
            width=BUTTON_WIDTH,
        )

        button_area = ft.Row([
            self.btn_start,
            self.btn_show_all,
            self.btn_show_unselected,
        ], alignment=ft.MainAxisAlignment.CENTER)

        # 文件占用警告栏
        self._file_lock_warning = ft.Container(
            ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color=COLOR_WARNING_BORDER, size=18),
                ft.Text(
                    WARN_FILE_LOCKED,
                    color=COLOR_WARNING_BORDER, size=FONT_SIZE_SMALL,
                    weight=ft.FontWeight.BOLD,
                ),
            ], spacing=8),
            bgcolor=COLOR_WARNING_BG,
            border_radius=6,
            padding=ft.Padding(top=8, bottom=8, left=12, right=12),
            margin=ft.Margin(top=0, bottom=4, left=0, right=0),
            visible=False,
        )

        # 状态文字
        self.status_text = ft.Text("", size=FONT_SIZE_BODY, color=COLOR_HINT, italic=True)

        # 主布局
        self.main_column = ft.Column([
            ft.Text(APP_TITLE, size=FONT_SIZE_TITLE, weight=ft.FontWeight.BOLD),
            self.menu_bar,
            self.status_text,
            self._file_lock_warning,
            ft.Divider(),
            mode_control,
            self.temp_input_container,
            ft.Divider(),
            button_area,
            ft.Column([
                ft.Text("结果：", weight=ft.FontWeight.BOLD),
                self.result_area,
            ], expand=True),
        ], expand=True, scroll=ft.ScrollMode.ALWAYS)

        self._refresh_status()
        return self.main_column

    # ==================== 模式切换 ====================

    def on_mode_change(self, e):
        self.current_mode = e.control.value
        self._clear_selection_context()
        if self.current_mode == "temporary":
            self.temp_input_container.visible = True
            self.temp_count_input.disabled = False
        else:
            self.temp_input_container.visible = False
            self.temp_count_input.disabled = True
        self.temp_input_container.update()
        self.temp_count_input.update()

    # ==================== 人数校验 ====================

    @staticmethod
    def _validate_count_value(raw: str) -> tuple[bool, str | None]:
        """校验人数输入是否合法（1~20 正整数）。
        返回 (是否合法, 错误信息或 None)
        """
        raw = raw.strip()
        try:
            val = int(raw)
            if val < MIN_SELECTION_COUNT:
                return False, f"人数不能小于 {MIN_SELECTION_COUNT}"
            if val > MAX_SELECTION_COUNT:
                return False, f"人数不能超过 {MAX_SELECTION_COUNT}"
            return True, None
        except ValueError:
            return False, "请输入有效的正整数"

    def _on_temp_count_change(self, e):
        """临时模式人数输入实时校验（事件处理器）"""
        self._apply_temp_count_validation(e.control)

    def _apply_temp_count_validation(self, control: ft.TextField):
        """根据输入值更新输入框和错误提示的外观"""
        raw = (control.value or "").strip()
        valid, error = self._validate_count_value(raw)

        if error:
            control.border_color = COLOR_DANGER
            self._temp_count_error.value = f"⚠ {error}"
            self._temp_count_error.visible = True
        else:
            control.border_color = COLOR_PRIMARY
            self._temp_count_error.visible = False

        control.update()
        self._temp_count_error.update()

    def _is_temp_count_valid(self) -> bool:
        raw = (self.temp_count_input.value or "").strip()
        try:
            val = int(raw)
            return MIN_SELECTION_COUNT <= val <= MAX_SELECTION_COUNT
        except ValueError:
            return False

    # ==================== 文件占用管理 ====================

    def _safe_save(self) -> bool:
        """安全保存：捕获文件占用异常，触发锁定警告。返回 True 表示保存成功。"""
        try:
            self.personnel_manager.save_data()
            return True
        except (PermissionError, OSError):
            self._handle_file_locked()
            return False

    def _handle_file_locked(self):
        """文件被占用时：显示警告并禁用拖地模式"""
        self._update_lock_warning(True)
        self._disable_mopping_mode()

    def _handle_file_unlocked(self):
        """文件恢复可写时：隐藏警告并恢复拖地模式"""
        self._update_lock_warning(False)
        self._enable_mopping_mode()

    def _update_lock_warning(self, visible: bool):
        if self._file_lock_warning is not None and self._file_lock_warning.page is not None:
            self._file_lock_warning.visible = visible
            self._file_lock_warning.update()

    def _disable_mopping_mode(self):
        if self._mopping_radio is not None and self._mopping_radio.page is not None:
            self._mopping_radio.disabled = True
            self._mopping_radio.update()

        if self.current_mode == "mopping":
            self.current_mode = "temporary"
            self.mode_group.value = "temporary"
            self.mode_group.update()
            self.temp_input_container.visible = True
            self.temp_input_container.disabled = False
            self.temp_input_container.update()
            self.temp_count_input.disabled = False
            self.temp_count_input.update()

    def _enable_mopping_mode(self):
        if self._mopping_radio is not None:
            self._mopping_radio.disabled = False
            if self._mopping_radio.page is not None:
                self._mopping_radio.update()

    def setup_file_monitor(self):
        """初始化并启动文件占用监测"""
        self._file_monitor = FileLockMonitor(
            get_file_path=lambda: self.personnel_manager.file_path,
            on_locked=self._handle_file_locked,
            on_unlocked=self._handle_file_unlocked,
        )
        self._file_monitor.start()

    # ==================== 开始选择 ====================

    def start_selection(self, _e):
        self._clear_selection_context()
        self.result_area.controls.clear()

        if self._is_file_locked and self.current_mode == "mopping":
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_FILE_LOCKED_SELECTION),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(f"{WARN_LOAD_FAILED}（{self.personnel_manager.file_name}），请通过「文件 → 打开数据文件」指定有效文件"),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        if self.current_mode == "temporary":
            self._temporary_mode_selection()
        else:
            self._mopping_mode_selection(_e)

    # ==================== 临时模式 ====================

    def _temporary_mode_selection(self):
        if not self._is_temp_count_valid():
            self._apply_temp_count_validation(self.temp_count_input)
            return

        count = int(self.temp_count_input.value.strip())

        all_personnel = self.personnel_manager.get_all_personnel()
        if all_personnel.empty:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_EMPTY_LIST),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        actual_count = min(count, len(all_personnel))
        selected_rows = all_personnel.sample(n=actual_count, random_state=self._random_state)

        self.display_selection_result(
            selected_rows, f"临时模式 - 已选择{actual_count}名人员", False
        )

        self._save_selection_context(selected_rows, "temporary")
        self.result_area.controls.extend(self._build_backtrack_panel())
        self.result_area.update()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    # ==================== 拖地模式 ====================

    def _mopping_mode_selection(self, e=None):
        if self._has_today_selection():
            if e is not None:
                show_mopping_redo_confirm(e.page, on_confirm=self._do_mopping_redo)
            else:
                self._do_mopping_selection()
            return
        self._do_mopping_selection()

    def _has_today_selection(self) -> bool:
        if not self.personnel_manager.load_data():
            return False
        df = self.personnel_manager.df
        today_str = datetime.now().strftime('%Y-%m-%d')
        mask = (df['是否已选'] == '是') & (
            df['选择时间'].astype(str).str.startswith(today_str)
        )
        return mask.any()

    def _do_mopping_redo(self):
        if not self.personnel_manager.load_data():
            return

        df = self.personnel_manager.df
        selected_mask = df['是否已选'] == '是'
        selected_df = df[selected_mask].copy()

        if not selected_df.empty:
            selected_df['_sort_time'] = pd.to_datetime(
                selected_df['选择时间'], errors='coerce'
            )
            latest_3 = selected_df.sort_values(
                '_sort_time', ascending=False
            ).head(3)

            self.personnel_manager.update_selection_status(
                latest_3.index, selected=False
            )
            self._safe_save()

        self._clear_selection_context()
        self.result_area.controls.clear()
        self._do_mopping_selection()

    def _do_mopping_selection(self):
        unselected_count = len(self.personnel_manager.get_unselected_personnel())

        if unselected_count >= MOPPING_COUNT:
            self._mopping_select_n(MOPPING_COUNT, unselected_count - MOPPING_COUNT)
        elif unselected_count > 0:
            self._mopping_select_n(unselected_count, 0)
        else:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_ALL_SELECTED),
                    bgcolor=COLOR_WARNING_BG,
                    padding=10,
                    border_radius=5,
                )
            )

        self.result_area.update()
        self._refresh_status()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    def _mopping_select_n(self, n: int, remaining: int):
        """从可选人员中随机选 n 人，标记已选并保存"""
        unselected_df = self.personnel_manager.get_unselected_personnel()
        selected_rows = unselected_df.sample(n=n, random_state=self._random_state)

        self.personnel_manager.update_selection_status(selected_rows.index, selected=True)
        self._safe_save()

        title = f"拖地模式 - 已选择{n}名人员"
        self.display_selection_result(selected_rows, title, True)

        # 显示剩余人数提示
        if remaining > 0:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(f"提示：剩余未选择人员：{remaining}名"),
                    bgcolor=COLOR_SUCCESS_BG,
                    padding=10,
                    border_radius=5,
                    margin=ft.Margin(top=10, bottom=0, left=0, right=0),
                )
            )
        else:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_ALL_SELECTED),
                    bgcolor=COLOR_WARNING_BG,
                    padding=10,
                    border_radius=5,
                    margin=ft.Margin(top=10, bottom=0, left=0, right=0),
                )
            )

        self._save_selection_context(selected_rows, "mopping")
        self.result_area.controls.extend(self._build_backtrack_panel())

    # ==================== 按钮禁用控制 ====================

    def _set_buttons_disabled(self, disabled: bool):
        for ctrl in [
            self.btn_start, self.btn_show_all, self.btn_show_unselected,
            self.btn_clear, self.mode_group, self.temp_count_input,
            self._backtrack_input, self._btn_backtrack,
        ]:
            if ctrl is not None and ctrl.page is not None:
                ctrl.disabled = disabled
                ctrl.update()

    # ==================== 回溯功能 ====================

    def _save_selection_context(self, selected_rows: pd.DataFrame, mode: str):
        self._last_selected_rows = selected_rows.copy()
        self._last_mode = mode

    def _clear_selection_context(self):
        self._last_selected_rows = None
        self._last_mode = None

    def _find_person_in_selection(self, student_id: str) -> tuple:
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            return None, None
        match = self._last_selected_rows[
            self._last_selected_rows['学号'].astype(str).str.strip() == str(student_id).strip()
        ]
        if match.empty:
            return None, None
        return match.index[0], match.iloc[0]

    def _show_backtrack_error(self, message: str):
        if self._backtrack_input is not None and self._backtrack_input.page is not None:
            self._backtrack_input.border_color = COLOR_DANGER
            self._backtrack_input.update()
        if self._backtrack_error is not None and self._backtrack_error.page is not None:
            self._backtrack_error.value = f"⚠ {message}"
            self._backtrack_error.color = COLOR_DANGER
            self._backtrack_error.visible = True
            self._backtrack_error.update()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=200)

    def _on_backtrack_input_change(self, e):
        raw = (e.control.value or "").strip()

        if not raw:
            e.control.border_color = None
            e.control.update()
            if self._backtrack_error is not None and self._backtrack_error.page is not None:
                self._backtrack_error.visible = False
                self._backtrack_error.update()
            return

        if self._last_selected_rows is None or self._last_selected_rows.empty:
            return

        idx, person_row = self._find_person_in_selection(raw)
        if idx is not None:
            name = safe_val(person_row['姓名'])
            e.control.border_color = COLOR_PRIMARY
            e.control.update()
            if self._backtrack_error is not None and self._backtrack_error.page is not None:
                self._backtrack_error.value = f"✓ 找到：{name}"
                self._backtrack_error.color = COLOR_SUCCESS_TEXT
                self._backtrack_error.visible = True
                self._backtrack_error.update()
                if self.main_column is not None:
                    self.main_column.scroll_to(key="backtrack_panel", duration=200)
        else:
            e.control.border_color = COLOR_DANGER
            e.control.update()
            if self._backtrack_error is not None and self._backtrack_error.page is not None:
                self._backtrack_error.value = "⚠ 该学号不在当前选中列表中"
                self._backtrack_error.color = COLOR_DANGER
                self._backtrack_error.visible = True
                self._backtrack_error.update()
                if self.main_column is not None:
                    self.main_column.scroll_to(key="backtrack_panel", duration=200)

    def _build_backtrack_panel(self) -> list:
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            return []

        self._backtrack_input = ft.TextField(
            label="输入要替换的学生学号",
            width=BACKTRACK_INPUT_WIDTH,
            keyboard_type=ft.KeyboardType.TEXT,
            text_align=ft.TextAlign.CENTER,
            on_change=self._on_backtrack_input_change,
        )
        self._backtrack_error = ft.Text("", size=12, color=COLOR_DANGER, visible=False)
        self._btn_backtrack = ft.ElevatedButton(
            BTN_BACKTRACK,
            on_click=self._do_backtrack,
            style=ft.ButtonStyle(bgcolor=COLOR_WARNING, color="white"),
            width=120,
        )

        return [
            ft.Container(key="backtrack_panel"),
            ft.Divider(),
            ft.Text("回溯替换：", weight=ft.FontWeight.BOLD, size=FONT_SIZE_BODY),
            ft.Text(HINT_BACKTRACK_USAGE, color=COLOR_HINT, size=FONT_SIZE_HINT, italic=True),
            ft.Row(
                [self._backtrack_input, self._btn_backtrack],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            ft.Row(
                [self._backtrack_error],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ]

    def _do_backtrack(self, _e):
        student_id = (self._backtrack_input.value or "").strip()

        if not student_id:
            self._show_backtrack_error("请输入学生学号")
            return

        if self._last_selected_rows is None or self._last_selected_rows.empty:
            self._show_backtrack_error("没有可回溯的选中结果，请先进行一次选择")
            return

        idx, person_row = self._find_person_in_selection(student_id)
        if idx is None:
            self._show_backtrack_error(
                f"学号为 {student_id} 的人员不在当前选中列表中，请检查输入"
            )
            return

        pos = list(self._last_selected_rows.index).index(idx)
        remaining = self._last_selected_rows.drop(idx)
        person_name = safe_val(person_row['姓名'])

        if self._last_mode == "temporary":
            all_personnel = self.personnel_manager.get_all_personnel()
            pool = all_personnel[~all_personnel.index.isin(remaining.index)]
        else:
            self.personnel_manager.update_selection_status([idx], selected=False)
            self._safe_save()
            unselected = self.personnel_manager.get_unselected_personnel()
            pool = unselected[~unselected.index.isin(remaining.index)]

        if pool.empty:
            if self._last_mode == "mopping":
                self.personnel_manager.update_selection_status([idx], selected=True)
                self._safe_save()
            self._show_backtrack_error("没有可用的替换人员，无法进行回溯")
            return

        replacement = pool.sample(n=1, random_state=self._random_state)
        replacement_idx = replacement.index[0]
        replacement_name = safe_val(replacement.iloc[0]['姓名'])

        if self._last_mode == "mopping":
            self.personnel_manager.update_selection_status([replacement_idx], selected=True)
            self._safe_save()

        parts_before = remaining.iloc[:pos]
        parts_after = remaining.iloc[pos:]
        new_selection = pd.concat([parts_before, replacement, parts_after], ignore_index=False)
        self._last_selected_rows = new_selection

        title = f"回溯替换 - 已将 {person_name}({student_id}) 替换为 {replacement_name}"
        self.display_selection_result(
            new_selection, title,
            saved_to_file=(self._last_mode == "mopping"),
            animate=False,
        )

        self.result_area.controls.extend(self._build_backtrack_panel())
        self.result_area.update()
        self._refresh_status()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    # ==================== 结果显示 ====================

    def _animate_table_fill(
        self, table: ft.DataTable, rows_data: list, start_index: int,
        scroll_target: str | None, live_text: ft.Text | None,
        animate: bool = True,
    ):
        if not animate:
            for i, (_, row) in enumerate(rows_data, start_index):
                cells = make_row_cells(i, row)
                color = COLOR_ROW_ALT if i % 2 == 0 else None
                table.rows.append(ft.DataRow(cells=cells, color=color))
            table.update()
            if rows_data and live_text is not None:
                _, last_row = rows_data[-1]
                name = safe_val(last_row['姓名'])
                live_text.value = f"🎯 {name}"
                live_text.update()
            return

        for i, (_, row) in enumerate(rows_data, start_index):
            cells = make_row_cells(i, row)

            if live_text is not None:
                name = safe_val(row['姓名'])
                live_text.value = f"🎯 {name}"
                live_text.update()

            table.rows.append(ft.DataRow(cells=cells, color=COLOR_ROW_HIGHLIGHT))

            if i > start_index:
                prev_idx = i - start_index - 1
                table.rows[prev_idx].color = COLOR_ROW_ALT if (i - start_index) % 2 == 0 else None

            table.update()
            if self.main_column is not None and scroll_target is not None:
                self.main_column.scroll_to(key=scroll_target, duration=200)
            time.sleep(ANIMATION_DELAY)

        if table.rows:
            last = len(table.rows) - 1
            table.rows[last].color = COLOR_ROW_ALT if len(table.rows) % 2 == 0 else None
            table.update()

    def display_selection_result(
        self, selected_rows: pd.DataFrame, title: str,
        saved_to_file: bool, animate: bool = True,
    ):
        self.result_area.controls.clear()
        count = len(selected_rows)

        live_name_text = ft.Text(
            "准备抽取...",
            size=FONT_SIZE_LIVE,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
            color="#1a1a1a",
        )
        live_display = ft.Container(
            ft.Column(
                [
                    ft.Text("当前选中", size=FONT_SIZE_BODY, color=COLOR_SUBTLE,
                            text_align=ft.TextAlign.CENTER),
                    live_name_text,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            bgcolor=COLOR_LIGHT_BG,
            border_radius=12,
            padding=ft.Padding(top=20, bottom=20, left=20, right=20),
            margin=ft.Margin(top=0, bottom=16, left=0, right=0),
            alignment=ft.alignment.center,
        )

        result_cards: list = [
            ft.Text(title, size=FONT_SIZE_SECTION, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            live_display,
        ]

        if not saved_to_file:
            result_cards.append(
                ft.Container(
                    ft.Text(HINT_TEMP_NOT_SAVED, color=COLOR_HINT),
                    margin=ft.Margin(top=0, bottom=10, left=0, right=0),
                )
            )

        if animate:
            self._set_buttons_disabled(True)

        try:
            if count <= 2:
                table = make_selection_table()
                table_row = ft.Row([table], scroll=ft.ScrollMode.AUTO, key="sel_table")
                result_cards.append(table_row)
                self.result_area.controls.extend(result_cards)
                self.result_area.page.update()

                self._animate_table_fill(
                    table, list(selected_rows.iterrows()), 1,
                    "sel_table", live_name_text, animate=animate,
                )
            else:
                mid = (count + 1) // 2
                left_rows = list(selected_rows.iloc[:mid].iterrows())
                right_rows = list(selected_rows.iloc[mid:].iterrows())

                left_table = make_selection_table()
                right_table = make_selection_table()

                left_col = ft.Column(
                    [left_table], expand=True, scroll=ft.ScrollMode.AUTO, key="left_table"
                )
                right_col = ft.Column(
                    [right_table], expand=True, scroll=ft.ScrollMode.AUTO, key="right_table"
                )

                split_row = ft.Row(
                    [left_col, ft.VerticalDivider(width=1, color=COLOR_BORDER), right_col],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                result_cards.append(split_row)
                self.result_area.controls.extend(result_cards)
                self.result_area.page.update()

                self._animate_table_fill(
                    left_table, left_rows, 1,
                    "left_table", live_name_text, animate=animate,
                )
                self._animate_table_fill(
                    right_table, right_rows, mid + 1,
                    "right_table", live_name_text, animate=animate,
                )
        finally:
            if animate:
                self._set_buttons_disabled(False)

    # ==================== 清空记录 ====================

    def clear_records(self):
        self._clear_selection_context()
        if not self.personnel_manager.load_data():
            self.result_area.controls.clear()
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_LOAD_FAILED),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        selected_count = (self.personnel_manager.df['是否已选'] == '是').sum()
        if selected_count == 0:
            self.result_area.controls.clear()
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("提示：没有人员被选中，无需清空"),
                    bgcolor=COLOR_NEUTRAL_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        self.personnel_manager.clear_selection_records()
        self.personnel_manager.save_data()

        self.result_area.controls.clear()
        self.result_area.controls.append(
            ft.Container(
                ft.Text("清空名单记录完成！"),
                bgcolor=COLOR_SUCCESS_BG,
                padding=10,
                border_radius=5,
            )
        )
        self.result_area.controls.extend([
            ft.Container(
                ft.Text(f"已重置 {selected_count} 名人员的选择状态"),
                margin=ft.Margin(top=5, bottom=0, left=0, right=0),
            ),
            ft.Container(
                ft.Text("现在所有人员都可以被重新选择"),
                margin=ft.Margin(top=5, bottom=0, left=0, right=0),
            ),
        ])
        self.result_area.update()
        self._refresh_status()

    # ==================== 人员查看 ====================

    def show_all_personnel(self, e):
        self._clear_selection_context()
        self.result_area.controls.clear()

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_LOAD_FAILED),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        all_personnel = self.personnel_manager.get_all_personnel()
        split_tables = build_split_personnel_tables(all_personnel, include_status=True)

        total = len(all_personnel)
        selected_count = (all_personnel['是否已选'] == '是').sum()

        self.result_area.controls.extend([
            ft.Text("所有人员信息", size=FONT_SIZE_SECTION, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            split_tables,
            ft.Container(
                ft.Text(
                    f"统计：总人数 {total}，已选择 {selected_count}，"
                    f"未选择 {total - selected_count}"
                ),
                bgcolor=COLOR_INFO_BG,
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=10, bottom=0, left=0, right=0),
            ),
        ])
        e.page.update()

    def show_unselected_personnel(self, e):
        self._clear_selection_context()
        self.result_area.controls.clear()

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_LOAD_FAILED),
                    bgcolor=COLOR_ERROR_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        unselected_df = self.personnel_manager.get_unselected_personnel()

        if unselected_df.empty:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(WARN_ALL_SELECTED),
                    bgcolor=COLOR_SUCCESS_BG,
                    padding=10,
                    border_radius=5,
                )
            )
            self.result_area.update()
            return

        split_tables = build_split_personnel_tables(unselected_df, include_status=False)

        self.result_area.controls.extend([
            ft.Text(
                f"未选择的人员（共{len(unselected_df)}名）",
                size=FONT_SIZE_SECTION, weight=ft.FontWeight.BOLD,
            ),
            ft.Divider(),
            split_tables,
        ])
        e.page.update()
