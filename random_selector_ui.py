"""随机选择人员系统 — UI 层"""
import flet as ft
import pandas as pd
import time
from datetime import datetime
from pathlib import Path

from config import DATA_DIR, load_settings, save_settings
from personnel_manager import PersonnelManager
from ui_helpers import (
    safe_val, make_selection_table, make_row_cells,
    build_split_personnel_tables,
    menu_item, not_implemented, show_about_dialog, show_help_dialog,
)


class RandomSelectorUI:
    def __init__(self):
        self.personnel_manager = PersonnelManager()
        self.result_area = None
        self.current_mode = "temporary"
        self.mode_group = None
        self.temp_count_input = None
        self.temp_input_container = None
        self.btn_start = None
        self.btn_show_all = None
        self.btn_show_unselected = None
        self.btn_clear = None
        self.main_column = None

        # 回溯功能状态
        self._last_selected_rows = None   # 当前抽选结果 DataFrame
        self._last_mode = None            # 当前抽选模式

        # 回溯功能 UI 控件引用（每次 _build_backtrack_panel 时重建）
        self._backtrack_input = None
        self._btn_backtrack = None

        # 状态显示
        self.status_text = None

        # 菜单栏与文件选择
        self.menu_bar = None
        self.file_picker = None

        # 种子设置（从配置文件加载）
        settings = load_settings()
        self._seed_enabled = settings.get("seed_enabled", False)
        self._seed_value = settings.get("seed_value", 42)

    @property
    def _random_state(self):
        """返回随机种子（启用时），否则返回 None 使用系统随机"""
        return self._seed_value if self._seed_enabled else None

    def _refresh_status(self):
        """刷新状态栏：显示文件内可读取的人数"""
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

    # ==================== 菜单栏与文件选择 ====================

    def _build_menu_bar(self):
        """构建菜单栏"""
        self.menu_bar = ft.MenuBar(
            expand=True,
            controls=[
                # ========== 文件 ==========
                ft.SubmenuButton(
                    content=ft.Text("文件"),
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
                # ========== 编辑 ==========
                ft.SubmenuButton(
                    content=ft.Text("编辑"),
                    controls=[
                        menu_item("清空选择记录...", "",
                                  icon=ft.Icon(ft.Icons.CLEAR_ALL),
                                  on_click=self._on_clear_records_menu),
                    ],
                ),
                # ========== 视图 ==========
                ft.SubmenuButton(
                    content=ft.Text("视图"),
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
                # ========== 工具 ==========
                ft.SubmenuButton(
                    content=ft.Text("工具"),
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
                # ========== 帮助 ==========
                ft.SubmenuButton(
                    content=ft.Text("帮助"),
                    controls=[
                        menu_item("使用说明", "",
                                  icon=ft.Icon(ft.Icons.HELP_OUTLINE),
                                  on_click=show_help_dialog),
                        ft.MenuItemButton(),
                        menu_item("关于...", "",
                                  icon=ft.Icon(ft.Icons.INFO_OUTLINE),
                                  on_click=show_about_dialog),
                    ],
                ),
            ],
        )
        return self.menu_bar

    def _on_open_file_click(self, _e):
        """点击"打开数据文件"菜单项"""
        if self.file_picker is not None:
            self.file_picker.pick_files(
                allowed_extensions=["xlsx"],
                dialog_title="选择人员数据文件",
                file_type=ft.FilePickerFileType.CUSTOM,
            )

    def _on_clear_records_menu(self, e):
        """菜单栏触发的清空记录"""
        self._confirm_clear_records(e)

    def _on_show_all_menu(self, _e):
        """菜单栏触发的查看所有人员"""
        if self.btn_show_all is not None:
            self.show_all_personnel(_e)

    def _on_show_unselected_menu(self, _e):
        """菜单栏触发的查看未选择人员"""
        if self.btn_show_unselected is not None:
            self.show_unselected_personnel(_e)

    # ==================== 选项对话框 ====================

    def _on_options_click(self, e):
        """打开选项配置对话框"""
        page = e.page

        seed_checkbox = ft.Checkbox(
            label="启用固定种子 (Seed)",
            value=self._seed_enabled,
        )
        seed_input = ft.TextField(
            label="种子值",
            value=str(self._seed_value),
            width=120,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            disabled=not self._seed_enabled,
        )

        def on_checkbox_change(_e):
            seed_input.disabled = not seed_checkbox.value
            seed_input.update()

        seed_checkbox.on_change = on_checkbox_change

        def on_confirm(_e):
            # 读取并校验种子值
            try:
                val = int(seed_input.value)
                if val < 0:
                    raise ValueError
            except ValueError:
                seed_input.error_text = "请输入非负整数"
                seed_input.update()
                return

            # 保存设置
            self._seed_enabled = seed_checkbox.value
            self._seed_value = val
            save_settings({
                "seed_enabled": self._seed_enabled,
                "seed_value": self._seed_value,
            })

            # 关闭对话框
            page.close(dialog)

        def on_cancel(_e):
            page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("选项"),
            content=ft.Column(
                [
                    seed_checkbox,
                    ft.Row([ft.Text("种子值："), seed_input]),
                    ft.Text(
                        "💡 相同种子 + 相同数据文件 = 相同的抽选结果",
                        size=12,
                        color="#888888",
                        italic=True,
                    ),
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("取消", on_click=on_cancel),
                ft.TextButton("确定", on_click=on_confirm),
            ],
        )

        page.open(dialog)

    # ==================== 导出结果 ====================

    def _on_export_results(self, _e):
        """导出本次抽选结果到 txt 文件"""
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            self._show_result_error("没有可导出的抽选结果，请先进行一次选择")
            return

        # 创建导出目录
        export_dir = DATA_DIR / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"抽选结果_{timestamp}.txt"
        file_path = export_dir / file_name

        # 构建导出内容
        mode_label = "拖地模式" if self._last_mode == "mopping" else "临时模式"
        lines = [
            "=" * 40,
            "随机选择人员系统 - 抽选结果",
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
        lines.extend([
            "",
            "=" * 40,
        ])

        # 写入文件
        try:
            file_path.write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            self._show_result_error(f"导出失败：无法写入文件 {file_name}")
            return

        # 成功提示
        self._remove_result_errors()
        self.result_area.controls.insert(
            0,
            ft.Container(
                ft.Text(
                    f"导出成功！文件已保存至：config/data/exports/{file_name}",
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor="#e8f5e9",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=10, left=0, right=0),
            ),
        )
        self.result_area.update()

    def _show_result_error(self, message):
        """在结果区域顶部显示错误提示（与回溯错误风格一致）"""
        self._remove_result_errors()
        self.result_area.controls.insert(
            0,
            ft.Container(
                ft.Text(message, color="#B71C1C", weight=ft.FontWeight.BOLD),
                bgcolor="#ffebee",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=10, left=0, right=0),
            ),
        )
        self.result_area.update()

    def _remove_result_errors(self):
        """移除结果区域中已有的错误提示"""
        to_remove = [
            c for c in self.result_area.controls
            if isinstance(c, ft.Container) and getattr(c, 'bgcolor', None) == "#ffebee"
        ]
        for c in to_remove:
            self.result_area.controls.remove(c)

    def _on_file_picked(self, e: ft.FilePickerResultEvent):
        """用户选择文件后的回调"""
        if e.files is None or len(e.files) == 0:
            return  # 用户取消了选择

        new_path = Path(e.files[0].path)
        # 更新数据管理器
        self.personnel_manager.set_file_path(new_path)

        # 清空结果显示区域
        self.result_area.controls.clear()
        self.result_area.controls.append(
            ft.Container(
                ft.Text(f"已切换数据文件：{new_path.name}", weight=ft.FontWeight.BOLD),
                bgcolor="#e8f5e9",
                padding=10,
                border_radius=5,
            )
        )
        self.result_area.update()

        # 清除回溯上下文并刷新状态
        self._clear_selection_context()
        self._refresh_status()

    def build_main_view(self):
        """构建主界面"""
        self.result_area = ft.Column([])

        # 文件选择器（需通过 page.overlay 挂载）
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)

        # 菜单栏
        self._build_menu_bar()

        # 模式选择
        self.mode_group = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(label="临时模式（不保存状态）", value="temporary"),
                ft.Radio(label="拖地模式（选择3人，保存状态）", value="mopping")
            ]),
            value="temporary",
            on_change=self.on_mode_change
        )

        self.btn_clear = ft.ElevatedButton(
            "清空记录",
            on_click=self._confirm_clear_records,
            style=ft.ButtonStyle(bgcolor="#f44336", color="white"),
            width=150
        )

        mode_control = ft.Column([
            ft.Text("选择模式：", weight=ft.FontWeight.BOLD),
            self.mode_group,
            self.btn_clear
        ])

        # 临时模式的输入
        self.temp_count_input = ft.TextField(
            label="选择人数",
            value="1",
            width=100,
            keyboard_type=ft.KeyboardType.NUMBER,
            text_align=ft.TextAlign.CENTER,
            visible=True
        )

        # 创建包裹输入框的容器
        self.temp_input_container = ft.Column([
            ft.Row([
                ft.Text("选择人数："),
                self.temp_count_input
            ], alignment=ft.MainAxisAlignment.CENTER)
        ], visible=True)

        # 按钮区域
        self.btn_start = ft.ElevatedButton(
            "开始选择",
            on_click=self.start_selection,
            style=ft.ButtonStyle(bgcolor="#4CAF50", color="white"),
            width=150
        )
        self.btn_show_all = ft.ElevatedButton(
            "查看所有人员",
            on_click=self.show_all_personnel,
            width=150
        )
        self.btn_show_unselected = ft.ElevatedButton(
            "查看未选择人员",
            on_click=self.show_unselected_personnel,
            width=150
        )

        button_area = ft.Row([
            self.btn_start,
            self.btn_show_all,
            self.btn_show_unselected,
        ], alignment=ft.MainAxisAlignment.CENTER)

        # 组合所有元素
        self.status_text = ft.Text("", size=14, color="#666666", italic=True)
        self.main_column = ft.Column([
            ft.Text("随机选择人员系统", size=24, weight=ft.FontWeight.BOLD),
            self.menu_bar,
            self.status_text,
            ft.Divider(),
            mode_control,

            # 临时模式的特定控件
            self.temp_input_container,

            ft.Divider(),
            button_area,

            # 结果显示区域
            ft.Column([
                ft.Text("结果：", weight=ft.FontWeight.BOLD),
                self.result_area
            ], expand=True)
        ], expand=True, scroll=ft.ScrollMode.ALWAYS)

        self._refresh_status()
        return self.main_column

    def on_mode_change(self, e):
        """模式改变时的处理"""
        self.current_mode = e.control.value
        self._clear_selection_context()
        # 根据模式显示/隐藏人数输入框
        if self.current_mode == "temporary":
            self.temp_input_container.visible = True
            self.temp_count_input.disabled = False  # 激活输入框
        else:
            self.temp_input_container.visible = False
            self.temp_count_input.disabled = True   # 未激活输入框
        self.temp_input_container.update()
        self.temp_count_input.update()

    def start_selection(self, _e):
        """开始选择"""
        self._clear_selection_context()
        self.result_area.controls.clear()

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(f"错误：无法加载数据文件（{self.personnel_manager.file_name}），请通过「文件 → 打开数据文件」指定有效文件"),
                    bgcolor="#ffebee",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        if self.current_mode == "temporary":
            self.temporary_mode_selection()
        else:
            self.mopping_mode_selection()

    def temporary_mode_selection(self):
        """临时模式选择"""
        try:
            count = int(self.temp_count_input.value) if self.temp_count_input.value else 1
            if count <= 0:
                count = 1
        except ValueError:
            count = 1

        # 获取所有人员（临时模式忽略选择状态）
        all_personnel = self.personnel_manager.get_all_personnel()

        if all_personnel.empty:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("人员名单为空！"),
                    bgcolor="#ffebee",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        # 限制选择人数
        actual_count = min(count, len(all_personnel))

        # 随机选择
        selected_rows = all_personnel.sample(n=actual_count, random_state=self._random_state)

        # 显示结果
        self.display_selection_result(selected_rows, f"临时模式 - 已选择{actual_count}名人员", False)

        # 保存回溯上下文并追加回溯面板
        self._save_selection_context(selected_rows, "temporary")
        self.result_area.controls.extend(self._build_backtrack_panel())
        self.result_area.update()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    def mopping_mode_selection(self):
        """拖地模式选择"""
        unselected_count = len(self.personnel_manager.get_unselected_personnel())

        if unselected_count >= 3:
            # 选择3人
            unselected_df = self.personnel_manager.get_unselected_personnel()
            selected_rows = unselected_df.sample(n=3, random_state=self._random_state)
            indices = selected_rows.index

            # 更新选择状态
            self.personnel_manager.update_selection_status(indices, selected=True)
            self.personnel_manager.save_data()

            # 显示结果
            self.display_selection_result(selected_rows, "拖地模式 - 已选择3名人员", True)

            # 显示剩余人数
            self.result_area.controls.append(
                ft.Container(
                    ft.Text(f"提示：剩余未选择人员：{unselected_count - 3}名"),
                    bgcolor="#e8f5e9",
                    padding=10,
                    border_radius=5,
                    margin=ft.Margin(top=10, bottom=0, left=0, right=0)
                )
            )

            # 保存回溯上下文并追加回溯面板
            self._save_selection_context(selected_rows, "mopping")
            self.result_area.controls.extend(self._build_backtrack_panel())
        elif unselected_count > 0:
            # 不足3人，选择剩余人员
            unselected_df = self.personnel_manager.get_unselected_personnel()
            selected_rows = unselected_df.sample(n=unselected_count, random_state=self._random_state)
            indices = selected_rows.index

            # 更新选择状态
            self.personnel_manager.update_selection_status(indices, selected=True)
            self.personnel_manager.save_data()

            # 显示结果
            self.display_selection_result(selected_rows, f"拖地模式 - 已选择剩余{unselected_count}名人员", True)

            # 显示所有人员已选完
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("提示：所有人员都已被选择过！"),
                    bgcolor="#fff3e0",
                    padding=10,
                    border_radius=5,
                    margin=ft.Margin(top=10, bottom=0, left=0, right=0)
                )
            )

            # 保存回溯上下文并追加回溯面板
            self._save_selection_context(selected_rows, "mopping")
            self.result_area.controls.extend(self._build_backtrack_panel())
        else:
            # 所有人都已选择
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("提示：所有人员都已被选择过！"),
                    bgcolor="#fff3e0",
                    padding=10,
                    border_radius=5
                )
            )

        self.result_area.update()
        self._refresh_status()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    def _set_buttons_disabled(self, disabled: bool):
        """动画期间禁用/启用所有操作控件"""
        for ctrl in [
            self.btn_start, self.btn_show_all, self.btn_show_unselected,
            self.btn_clear, self.mode_group, self.temp_count_input,
            self._backtrack_input, self._btn_backtrack,
        ]:
            if ctrl is not None and ctrl.page is not None:
                ctrl.disabled = disabled
                ctrl.update()

    # ==================== 回溯功能 ====================

    def _save_selection_context(self, selected_rows, mode):
        """保存当前抽选上下文，供回溯使用"""
        self._last_selected_rows = selected_rows.copy()
        self._last_mode = mode

    def _clear_selection_context(self):
        """清除回溯上下文"""
        self._last_selected_rows = None
        self._last_mode = None

    def _find_person_in_selection(self, student_id):
        """在 _last_selected_rows 中按学号查找人员。
        返回 (index, row_series) 或 (None, None)
        """
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            return None, None
        match = self._last_selected_rows[
            self._last_selected_rows['学号'].astype(str).str.strip() == str(student_id).strip()
        ]
        if match.empty:
            return None, None
        return match.index[0], match.iloc[0]

    def _show_backtrack_error(self, message):
        """在结果区域顶部显示回溯错误信息"""
        self._show_result_error(message)

    def _build_backtrack_panel(self):
        """构建回溯 UI 面板，无上下文时返回空列表"""
        if self._last_selected_rows is None or self._last_selected_rows.empty:
            return []

        # 每次创建新的控件实例，避免 Flet 控件重新挂载导致事件丢失
        self._backtrack_input = ft.TextField(
            label="输入要替换的学生学号",
            width=200,
            keyboard_type=ft.KeyboardType.TEXT,
            text_align=ft.TextAlign.CENTER,
        )
        self._btn_backtrack = ft.ElevatedButton(
            "回溯替换",
            on_click=self._do_backtrack,
            style=ft.ButtonStyle(bgcolor="#FF9800", color="white"),
            width=120,
        )

        return [
            ft.Container(key="backtrack_panel"),
            ft.Divider(),
            ft.Text("回溯替换：", weight=ft.FontWeight.BOLD, size=14),
            ft.Text(
                "如选中人员请假或有特殊情况，可输入其学号进行回溯替换",
                color="#666666", size=12, italic=True,
            ),
            ft.Row(
                [self._backtrack_input, self._btn_backtrack],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        ]

    def _do_backtrack(self, _e):
        """执行回溯替换操作"""
        student_id = (self._backtrack_input.value or "").strip()

        # 1. 校验输入
        if not student_id:
            self._show_backtrack_error("请输入学生学号")
            return

        if self._last_selected_rows is None or self._last_selected_rows.empty:
            self._show_backtrack_error("没有可回溯的选中结果，请先进行一次选择")
            return

        # 2. 在当前抽选结果中查找
        idx, person_row = self._find_person_in_selection(student_id)
        if idx is None:
            self._show_backtrack_error(
                f"学号为 {student_id} 的人员不在当前选中列表中，请检查输入"
            )
            return

        # 3. 记录被排除者在原表格中的位置，构建剩余列表
        pos = list(self._last_selected_rows.index).index(idx)  # 整数位置
        remaining = self._last_selected_rows.drop(idx)
        person_name = safe_val(person_row['姓名'])

        # 4. 确定替换人员池（模式相关）
        if self._last_mode == "temporary":
            # 临时模式：池 = 全部人员 - 剩余选中人员
            all_personnel = self.personnel_manager.get_all_personnel()
            pool = all_personnel[~all_personnel.index.isin(remaining.index)]
        else:
            # 拖地模式：先还原被排除者的状态
            self.personnel_manager.update_selection_status([idx], selected=False)
            self.personnel_manager.save_data()

            # 池 = 未选人员 - 剩余选中人员
            unselected = self.personnel_manager.get_unselected_personnel()
            pool = unselected[~unselected.index.isin(remaining.index)]

        # 5. 检查是否有可用的替换人员
        if pool.empty:
            if self._last_mode == "mopping":
                # 回滚：恢复被排除者的选中状态
                self.personnel_manager.update_selection_status([idx], selected=True)
                self.personnel_manager.save_data()
            self._show_backtrack_error("没有可用的替换人员，无法进行回溯")
            return

        # 6. 随机选择替换人员
        replacement = pool.sample(n=1, random_state=self._random_state)
        replacement_idx = replacement.index[0]
        replacement_name = safe_val(replacement.iloc[0]['姓名'])

        # 7. 拖地模式：标记替换者为已选并保存
        if self._last_mode == "mopping":
            self.personnel_manager.update_selection_status([replacement_idx], selected=True)
            self.personnel_manager.save_data()

        # 8. 构建新的选中列表（替换人员插入到被排除者的原位置）
        parts_before = remaining.iloc[:pos]
        parts_after = remaining.iloc[pos:]
        new_selection = pd.concat([parts_before, replacement, parts_after], ignore_index=False)
        self._last_selected_rows = new_selection

        # 9. 显示更新结果
        title = (
            f"回溯替换 - 已将 {person_name}({student_id}) 替换为 {replacement_name}"
        )
        self.display_selection_result(
            new_selection,
            title,
            saved_to_file=(self._last_mode == "mopping"),
            animate=False,
        )

        # 10. 重新追加回溯面板并滚动到可见位置
        self.result_area.controls.extend(self._build_backtrack_panel())
        self.result_area.update()
        self._refresh_status()
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    # ==================== 结果显示 ====================

    def _animate_table_fill(self, table, rows_data, start_index, scroll_target, animate=True):
        """逐行动画填充一个表格。animate=False 时直接全部填充，无延迟。"""
        if not animate:
            # 直接填充所有行，无动画
            for i, (_, row) in enumerate(rows_data, start_index):
                cells = make_row_cells(i, row)
                color = "#fff8e1" if i % 2 == 0 else None
                table.rows.append(ft.DataRow(cells=cells, color=color))
            table.update()
            return

        for i, (_, row) in enumerate(rows_data, start_index):
            cells = make_row_cells(i, row)

            # 新行亮黄高亮
            table.rows.append(ft.DataRow(cells=cells, color="#FFF9C4"))

            # 上一行恢复交替色
            if i > start_index:
                prev_idx = i - start_index - 1
                table.rows[prev_idx].color = "#fff8e1" if (i - start_index) % 2 == 0 else None

            table.update()
            # 自动滚动到当前表格区域
            if self.main_column is not None and scroll_target is not None:
                self.main_column.scroll_to(key=scroll_target, duration=200)
            time.sleep(0.35)

        # 最后一行恢复正常色
        if table.rows:
            last = len(table.rows) - 1
            table.rows[last].color = "#fff8e1" if len(table.rows) % 2 == 0 else None
            table.update()

    def display_selection_result(self, selected_rows, title, saved_to_file, animate=True):
        """显示选择结果。animate=False 时跳过逐行动画，直接渲染。"""
        self.result_area.controls.clear()

        count = len(selected_rows)
        result_cards = [
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            ft.Divider()
        ]

        # 提示信息
        if not saved_to_file:
            result_cards.append(
                ft.Container(
                    ft.Text("提示：此为临时选择，未保存到原文件", color="#666666"),
                    margin=ft.Margin(top=0, bottom=10, left=0, right=0)
                )
            )

        # 动画期间需要禁用按钮
        if animate:
            self._set_buttons_disabled(True)

        try:
            # ≤2人：单表
            if count <= 2:
                table = make_selection_table()
                table_row = ft.Row([table], scroll=ft.ScrollMode.AUTO, key="sel_table")
                result_cards.append(table_row)
                self.result_area.controls.extend(result_cards)
                self.result_area.page.update()

                self._animate_table_fill(table, list(selected_rows.iterrows()), 1, "sel_table", animate=animate)

            # >2人：双表平铺，先左后右
            else:
                mid = (count + 1) // 2
                left_rows = list(selected_rows.iloc[:mid].iterrows())
                right_rows = list(selected_rows.iloc[mid:].iterrows())

                left_table = make_selection_table()
                right_table = make_selection_table()

                left_col = ft.Column([left_table], expand=True, scroll=ft.ScrollMode.AUTO, key="left_table")
                right_col = ft.Column([right_table], expand=True, scroll=ft.ScrollMode.AUTO, key="right_table")

                split_row = ft.Row(
                    [left_col, ft.VerticalDivider(width=1, color="#e0e0e0"), right_col],
                    expand=True,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
                result_cards.append(split_row)
                self.result_area.controls.extend(result_cards)
                self.result_area.page.update()

                # 先填充左表
                self._animate_table_fill(left_table, left_rows, 1, "left_table", animate=animate)
                # 再填充右表
                self._animate_table_fill(right_table, right_rows, mid + 1, "right_table", animate=animate)

        finally:
            if animate:
                self._set_buttons_disabled(False)

    def _confirm_clear_records(self, e):
        """弹出二次确认窗口，确认后执行清空记录"""
        page = e.page

        def on_confirm(_e):
            page.close(dialog)
            self.clear_records(e)

        dialog = ft.AlertDialog(
            title=ft.Text("确认清空"),
            content=ft.Text("确定要清空所有选择记录吗？\n此操作不可撤销，所有人员的选中状态将被重置。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: page.close(dialog)),
                ft.TextButton("确定清空", on_click=on_confirm),
            ],
        )
        page.open(dialog)

    def clear_records(self, _e):
        """清空记录"""
        self._clear_selection_context()
        if not self.personnel_manager.load_data():
            self.result_area.controls.clear()
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("错误：无法加载数据文件"),
                    bgcolor="#ffebee",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        # 检查是否有记录需要清空
        selected_count = (self.personnel_manager.df['是否已选'] == '是').sum()
        if selected_count == 0:
            self.result_area.controls.clear()
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("提示：没有人员被选中，无需清空"),
                    bgcolor="#fff8e1",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        # 清空记录
        self.personnel_manager.clear_selection_records()
        self.personnel_manager.save_data()

        # 显示结果
        self.result_area.controls.clear()
        self.result_area.controls.append(
            ft.Container(
                ft.Text("清空名单记录完成！"),
                bgcolor="#e8f5e9",
                padding=10,
                border_radius=5
            )
        )
        self.result_area.controls.append(
            ft.Container(
                ft.Text(f"已重置 {selected_count} 名人员的选择状态"),
                margin=ft.Margin(top=5, bottom=0, left=0, right=0)
            )
        )
        self.result_area.controls.append(
            ft.Container(
                ft.Text("现在所有人员都可以被重新选择"),
                margin=ft.Margin(top=5, bottom=0, left=0, right=0)
            )
        )
        self.result_area.update()
        self._refresh_status()

    def show_all_personnel(self, e):
        """显示所有人员"""
        self._clear_selection_context()
        self.result_area.controls.clear()

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("错误：无法加载数据文件"),
                    bgcolor="#ffebee",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        all_personnel = self.personnel_manager.get_all_personnel()
        split_tables = build_split_personnel_tables(all_personnel, include_status=True)

        # 统计信息
        selected_count = (all_personnel['是否已选'] == '是').sum()
        total = len(all_personnel)

        self.result_area.controls.extend([
            ft.Text("所有人员信息", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            split_tables,
            ft.Container(
                ft.Text(
                    f"统计：总人数 {total}，已选择 {selected_count}，未选择 {total - selected_count}"),
                bgcolor="#e3f2fd",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=10, bottom=0, left=0, right=0)
            )
        ])
        e.page.update()

    def show_unselected_personnel(self, e):
        """显示未选择的人员"""
        self._clear_selection_context()
        self.result_area.controls.clear()

        if not self.personnel_manager.load_data():
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("错误：无法加载数据文件"),
                    bgcolor="#ffebee",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        unselected_df = self.personnel_manager.get_unselected_personnel()

        if unselected_df.empty:
            self.result_area.controls.append(
                ft.Container(
                    ft.Text("所有人员都已被选择！"),
                    bgcolor="#e8f5e9",
                    padding=10,
                    border_radius=5
                )
            )
            self.result_area.update()
            return

        split_tables = build_split_personnel_tables(unselected_df, include_status=False)

        self.result_area.controls.extend([
            ft.Text(f"未选择的人员（共{len(unselected_df)}名）", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            split_tables,
        ])
        e.page.update()
