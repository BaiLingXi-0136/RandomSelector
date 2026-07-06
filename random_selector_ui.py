import flet as ft
import pandas as pd
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
        self.temp_input_container = None  # 用于包裹临时模式输入框的容器

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

        mode_control = ft.Column([
            ft.Text("选择模式：", weight=ft.FontWeight.BOLD),
            self.mode_group,
            ft.ElevatedButton(
                "清空记录",
                on_click=self.clear_records,
                style=ft.ButtonStyle(bgcolor="#f44336", color="white"),
                width=150
            )
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
        button_area = ft.Row([
            ft.ElevatedButton(
                "开始选择",
                on_click=self.start_selection,
                style=ft.ButtonStyle(bgcolor="#4CAF50", color="white"),
                width=150
            ),
            ft.ElevatedButton(
                "查看所有人员",
                on_click=self.show_all_personnel,
                width=150
            ),
            ft.ElevatedButton(
                "查看未选择人员",
                on_click=self.show_unselected_personnel,
                width=150
            )
        ], alignment=ft.MainAxisAlignment.CENTER)

        # 组合所有元素
        return ft.Column([
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

    def on_mode_change(self, e):
        """模式改变时的处理"""
        self.current_mode = e.control.value
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

    def display_selection_result(self, selected_rows, title, saved_to_file):
        """显示选择结果"""
        result_cards = [
            ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            ft.Divider()
        ]

        # 人员信息
        for i, (_, row) in enumerate(selected_rows.iterrows(), 1):
            person_info = ft.Column([
                ft.Text(f"人员 {i}：", weight=ft.FontWeight.BOLD),
            ], spacing=2)

            # 显示所有列的信息，但跳过"是否已选"和"选择时间"列
            for col in selected_rows.columns:
                if col not in ['是否已选', '选择时间'] and pd.notna(row[col]):
                    person_info.controls.append(
                        ft.Text(f"{col}: {row[col]}", size=12)
                    )

            # 创建卡片
            card = ft.Container(
                person_info,
                bgcolor="#f5f5f5",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=5, left=0, right=0)
            )
            result_cards.append(card)

        # 添加说明
        if not saved_to_file:
            result_cards.append(
                ft.Container(
                    ft.Text("提示：此为临时选择，未保存到原文件", color="#666"),
                    margin=ft.Margin(top=10, bottom=0, left=0, right=0)
                )
            )

        self.result_area.controls.extend(result_cards)
        self.result_area.update()

    def clear_records(self, _e):
        """清空记录"""
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

    def show_all_personnel(self, e):
        """显示所有人员"""
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

        result_cards = [
            ft.Text("所有人员信息", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider()
        ]

        for i, (_, row) in enumerate(all_personnel.iterrows(), 1):
            person_info = ft.Column([
                ft.Text(f"人员 {i}：", weight=ft.FontWeight.BOLD),
            ], spacing=2)

            # 显示所有列的信息，跳过"是否已选"和"选择时间"列
            for col in all_personnel.columns:
                if col in ['是否已选', '选择时间']:
                    continue
                if pd.notna(row[col]):
                    person_info.controls.append(
                        ft.Text(f"{col}: {row[col]}", size=12)
                    )

            # 单独显示选择状态，使用醒目的颜色
            selected_status = row['是否已选'] if pd.notna(row['是否已选']) else '否'
            status_color = "#4CAF50" if selected_status == '是' else "#F44336"
            person_info.controls.append(
                ft.Text(f"是否已选: {selected_status}", size=12, color=status_color, weight=ft.FontWeight.BOLD)
            )

            card = ft.Container(
                person_info,
                bgcolor="#f5f5f5",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=5, left=0, right=0)
            )
            result_cards.append(card)

        # 统计信息
        selected_count = (all_personnel['是否已选'] == '是').sum()
        result_cards.append(
            ft.Container(
                ft.Text(
                    f"\n统计：总人数 {len(all_personnel)}，已选择 {selected_count}，未选择 {len(all_personnel) - selected_count}"),
                bgcolor="#e3f2fd",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=10, bottom=0, left=0, right=0)
            )
        )

        self.result_area.controls.extend(result_cards)
        # 使用 page.update() 进行完整刷新，确保嵌套控件正确渲染
        e.page.update()

    def show_unselected_personnel(self, e):
        """显示未选择的人员"""
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

        result_cards = [
            ft.Text(f"未选择的人员（共{len(unselected_df)}名）", size=18, weight=ft.FontWeight.BOLD),
            ft.Divider()
        ]

        for i, (_, row) in enumerate(unselected_df.iterrows(), 1):
            person_info = ft.Column([
                ft.Text(f"人员 {i}：", weight=ft.FontWeight.BOLD),
            ], spacing=2)

            for col in unselected_df.columns:
                if col in ['是否已选', '选择时间']:
                    continue
                if pd.notna(row[col]):
                    person_info.controls.append(
                        ft.Text(f"{col}: {row[col]}", size=12)
                    )

            card = ft.Container(
                person_info,
                bgcolor="#fff3e0",
                padding=10,
                border_radius=5,
                margin=ft.Margin(top=0, bottom=5, left=0, right=0)
            )
            result_cards.append(card)

        self.result_area.controls.extend(result_cards)
        # 使用 page.update() 进行完整刷新，确保嵌套控件正确渲染
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
