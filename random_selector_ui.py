import flet as ft
import pandas as pd
import time
from datetime import datetime
from pathlib import Path

# 设置数据目录
DATA_DIR = Path("data")
EXCEL_FILE = DATA_DIR / "PersonnelList.xlsx"


class PersonnelManager:
    def __init__(self):
        self.df = None

    def load_data(self) -> bool:
        """加载人员数据"""
        try:
            if not EXCEL_FILE.exists():
                return False
            self.df = pd.read_excel(EXCEL_FILE)
            if self.df.empty:
                return False
            # 确保选择标记列存在
            if '是否已选' not in self.df.columns:
                self.df['是否已选'] = '否'
            # 确保'选择时间'列存在且为字符串类型
            if '选择时间' not in self.df.columns:
                self.df['选择时间'] = ''
            else:
                # 转换现有数据为字符串类型
                self.df['选择时间'] = self.df['选择时间'].astype(str)
            return True
        except (Exception, FileNotFoundError):
            return False

    def get_unselected_personnel(self) -> pd.DataFrame:
        """获取未选择的人员"""
        if self.df is None:
            return pd.DataFrame()
        return self.df[self.df['是否已选'] == '否']

    def get_all_personnel(self) -> pd.DataFrame:
        """获取所有人员"""
        if self.df is None:
            return pd.DataFrame()
        return self.df.copy()

    def update_selection_status(self, indices, selected: bool = True):
        """更新选择状态"""
        if self.df is not None:
            for idx in indices:
                self.df.at[idx, '是否已选'] = '是' if selected else '否'
                if selected:
                    self.df.at[idx, '选择时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    # 确保选择时间列保持字符串类型
                    self.df['选择时间'] = self.df['选择时间'].astype(str)

    def save_data(self):
        """保存数据到文件"""
        if self.df is not None:
            self.df.to_excel(EXCEL_FILE, index=False)

    def clear_selection_records(self):
        """清空选择记录"""
        if self.df is not None:
            self.df['是否已选'] = '否'
            self.df['选择时间'] = ''


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

    def build_main_view(self):
        """构建主界面"""
        self.result_area = ft.Column([])

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
            on_click=self.clear_records,
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
        self.main_column = ft.Column([
            ft.Text("随机选择人员系统", size=24, weight=ft.FontWeight.BOLD),
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
                    ft.Text("错误：无法加载数据文件，请确保PersonnelList.xlsx存在于data目录中"),
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
        selected_rows = all_personnel.sample(n=actual_count)

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
            selected_rows = unselected_df.sample(n=3)
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
            selected_rows = unselected_df.sample(n=unselected_count)
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
        """在结果区域顶部显示回溯错误信息（仅保留最新一条）"""
        # 移除已有的错误提示
        to_remove = [
            c for c in self.result_area.controls
            if isinstance(c, ft.Container) and getattr(c, 'bgcolor', None) == "#ffebee"
        ]
        for c in to_remove:
            self.result_area.controls.remove(c)

        # 插入到结果区域最前面，确保可见
        self.result_area.controls.insert(
            0,
            ft.Container(
                ft.Text(message, color="#B71C1C", weight=ft.FontWeight.BOLD),
                bgcolor="#ffebee",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=10, left=0, right=0),
            )
        )
        self.result_area.update()

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
        person_name = self._safe_val(person_row['姓名'])

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
        replacement = pool.sample(n=1)
        replacement_idx = replacement.index[0]
        replacement_name = self._safe_val(replacement.iloc[0]['姓名'])

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
        if self.main_column is not None:
            self.main_column.scroll_to(key="backtrack_panel", duration=300)

    @staticmethod
    def _make_selection_table():
        """创建抽选结果用的空DataTable（不含是否已选列）"""
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("序号", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("姓名", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("学号", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("班级", weight=ft.FontWeight.BOLD, size=13)),
                ft.DataColumn(ft.Text("性别", weight=ft.FontWeight.BOLD, size=13)),
            ],
            rows=[],
            column_spacing=12,
            heading_row_height=38,
            data_row_min_height=32,
            data_row_max_height=40,
            border=ft.border.all(color="#e0e0e0", width=1),
            border_radius=8,
            show_bottom_border=True,
            heading_row_color="#E3F2FD",
        )

    @staticmethod
    def _make_row_cells(i, row, safe_val):
        """构建一行的DataCell列表"""
        return [
            ft.DataCell(ft.Text(str(i), size=13, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['姓名']), size=13)),
            ft.DataCell(ft.Text(safe_val(row['学号']), size=13, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['班级']), size=13, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['性别']), size=13, text_align=ft.TextAlign.CENTER)),
        ]

    def _animate_table_fill(self, table, rows_data, start_index, scroll_target, animate=True):
        """逐行动画填充一个表格。animate=False 时直接全部填充，无延迟。"""
        if not animate:
            # 直接填充所有行，无动画
            for i, (_, row) in enumerate(rows_data, start_index):
                cells = self._make_row_cells(i, row, self._safe_val)
                color = "#fff8e1" if i % 2 == 0 else None
                table.rows.append(ft.DataRow(cells=cells, color=color))
            table.update()
            return

        for i, (_, row) in enumerate(rows_data, start_index):
            cells = self._make_row_cells(i, row, self._safe_val)

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
                table = self._make_selection_table()
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

                left_table = self._make_selection_table()
                right_table = self._make_selection_table()

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

    @staticmethod
    def _safe_val(val):
        """安全获取单元格值，NaN转为空字符串"""
        return str(val) if pd.notna(val) else ""

    def _build_personnel_table(self, df, include_status=True, start_index=1):
        """构建人员信息DataTable"""
        columns = [
            ft.DataColumn(ft.Text("序号", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("姓名", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("学号", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("班级", weight=ft.FontWeight.BOLD, size=13)),
            ft.DataColumn(ft.Text("性别", weight=ft.FontWeight.BOLD, size=13)),
        ]
        if include_status:
            columns.append(ft.DataColumn(ft.Text("是否已选", weight=ft.FontWeight.BOLD, size=13)))

        table = ft.DataTable(
            columns=columns,
            rows=[],
            column_spacing=12,
            heading_row_height=38,
            data_row_min_height=32,
            data_row_max_height=40,
            border=ft.border.all(color="#e0e0e0", width=1),
            border_radius=8,
            show_bottom_border=True,
            heading_row_color="#E3F2FD",
        )

        for i, (_, row) in enumerate(df.iterrows(), start_index):
            selected = (include_status and row['是否已选'] == '是')

            cells = [
                ft.DataCell(ft.Text(str(i), size=13, text_align=ft.TextAlign.CENTER)),
                ft.DataCell(ft.Text(self._safe_val(row['姓名']), size=13)),
                ft.DataCell(ft.Text(self._safe_val(row['学号']), size=13, text_align=ft.TextAlign.CENTER)),
                ft.DataCell(ft.Text(self._safe_val(row['班级']), size=13, text_align=ft.TextAlign.CENTER)),
                ft.DataCell(ft.Text(self._safe_val(row['性别']), size=13, text_align=ft.TextAlign.CENTER)),
            ]

            if include_status:
                status_text = "是" if selected else "否"
                status_color = "#4CAF50" if selected else "#F44336"
                cells.append(
                    ft.DataCell(ft.Text(
                        status_text, size=13, color=status_color,
                        weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER
                    ))
                )

            # 已选行浅绿背景，未选行交替色便于阅读
            row_color = "#f1f8e9" if selected else ("#fff8e1" if i % 2 == 0 else None)
            table.rows.append(ft.DataRow(cells=cells, color=row_color))

        return table

    def _build_split_personnel_tables(self, df, include_status=True):
        """将数据对半拆分，返回左右两个表格平铺的Row"""
        mid = (len(df) + 1) // 2  # 向上取整，左表多一个

        left_df = df.iloc[:mid]
        right_df = df.iloc[mid:]

        left_table = self._build_personnel_table(left_df, include_status, start_index=1)
        right_table = self._build_personnel_table(
            right_df, include_status, start_index=mid + 1
        ) if len(right_df) > 0 else None

        tables = [
            ft.Column([left_table], expand=True, scroll=ft.ScrollMode.AUTO),
        ]
        if right_table is not None:
            tables.append(ft.VerticalDivider(width=1, color="#e0e0e0"))
            tables.append(ft.Column([right_table], expand=True, scroll=ft.ScrollMode.AUTO))

        return ft.Row(tables, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)

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
        split_tables = self._build_split_personnel_tables(all_personnel, include_status=True)

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

        split_tables = self._build_split_personnel_tables(unselected_df, include_status=False)

        self.result_area.controls.extend([
            ft.Text(f"未选择的人员（共{len(unselected_df)}名）", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            split_tables,
        ])
        e.page.update()


def main(page: ft.Page):
    """主函数"""
    page.title = "随机选择人员系统"
    page.theme_mode = ft.ThemeMode.LIGHT

    # 设置页面布局
    page.window_width = 800
    page.window_height = 600
    page.window_resizable = True

    # 创建应用实例
    app_ui = RandomSelectorUI()

    # 将主视图添加到页面
    page.add(app_ui.build_main_view())


if __name__ == "__main__":
    ft.app(target=main)
