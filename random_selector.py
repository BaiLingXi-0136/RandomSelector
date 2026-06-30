import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional, Union


class FileHandler:
    """文件处理基类"""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path

    def check_exists(self) -> bool:
        """检查文件是否存在"""
        if not self.file_path.exists():
            print(f"错误：找不到文件 {self.file_path}")
            return False
        return True

    def read_excel(self) -> Optional[pd.DataFrame]:
        """读取Excel文件并返回DataFrame"""
        try:
            df = pd.read_excel(self.file_path)
            if df.empty:
                print("错误：文件为空")
                return None
            return df
        except Exception as e:
            print(f"读取文件时发生错误：{str(e)}")
            return None


class DataValidator:
    """数据验证类"""

    @staticmethod
    def validate_personnel_data(df: pd.DataFrame) -> bool:
        """验证人员数据是否符合要求"""
        if '姓名' not in df.columns:
            print("错误：人员名单中必须有'姓名'列")
            return False
        return True


class PersonnelManager:
    """人员数据管理类"""

    def __init__(self, file_path: Union[str, Path]):
        self.file_handler = FileHandler(file_path)
        self.df: Optional[pd.DataFrame] = None

    def load_data(self) -> bool:
        """加载人员数据"""
        if not self.file_handler.check_exists():
            return False

        self.df = self.file_handler.read_excel()
        if self.df is None:
            return False

        if not DataValidator.validate_personnel_data(self.df):
            self.df = None
            return False

        return True

    def ensure_selection_columns(self):
        """确保选择标记列存在"""
        if self.df is not None and '是否已选' not in self.df.columns:
            self.df['是否已选'] = '否'
            print("已添加'是否已选'列到人员名单中")

    def get_unselected_count(self) -> int:
        """获取未选择的人员数量"""
        if self.df is None:
            return 0
        return (self.df['是否已选'] == '否').sum()

    def get_unselected_personnel(self) -> Optional[pd.DataFrame]:
        """获取未选择的人员"""
        if self.df is None:
            return None
        return self.df[self.df['是否已选'] == '否']

    def update_selection_status(self, indices, selected: bool = True):
        """更新选择状态"""
        if self.df is None:
            return

        for idx in indices:
            self.df.at[idx, '是否已选'] = '是' if selected else '否'
            # 确保选择时间列是字符串类型
            if selected and ('选择时间' not in self.df.columns or pd.isna(self.df['选择时间']).all()):
                self.df['选择时间'] = ''
            if selected:
                self.df.at[idx, '选择时间'] = str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def clear_selection_records(self):
        """清空选择记录"""
        if self.df is None:
            return
        self.df['是否已选'] = '否'
        if '选择时间' in self.df.columns:
            self.df['选择时间'] = self.df['选择时间'].apply(lambda x: '')

    def save_data(self):
        """保存数据到文件"""
        if self.df is not None:
            self.df.to_excel(self.file_handler.file_path, index=False)

    def get_copy(self) -> Optional[pd.DataFrame]:
        """获取数据副本"""
        if self.df is None:
            return None
        return self.df.copy()

    def get_all_personnel(self) -> Optional[pd.DataFrame]:
        """获取所有人员"""
        if self.df is None:
            return None
        return self.df.copy()


class DisplayManager:
    """显示管理类"""

    @staticmethod
    def display_person_info(person_info):
        """显示人员信息"""
        for col, value in person_info.items():
            if pd.notna(value):
                print(f"{col}: {value}")

    @staticmethod
    def display_selection_result(selected_rows, mode: str = "临时模式", count: Optional[int] = None):
        """显示选择结果"""
        print("\n" + "=" * 50)
        if count:
            print(f"{mode} - 已选择的{count}名人员信息：")
        else:
            print(f"{mode} - 已选择的人员信息：")
        print("=" * 50)

        for i, (_, row) in enumerate(selected_rows.iterrows(), 1):
            print(f"\n人员 {i}:")
            print("-" * 30)

            DisplayManager.display_person_info(row)

            # 如果需要显示选择状态
            if row.get('是否已选') == '是':
                print(f"是否已选: 是")
                # 处理选择时间，如果为空则使用当前时间
                selection_time = row.get('选择时间', '')
                if pd.isna(selection_time) or selection_time == '':
                    selection_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"选择时间: {selection_time}")


class TemporaryMode:
    """临时模式类"""

    def __init__(self, manager: PersonnelManager):
        self.manager = manager
        self.display_manager = DisplayManager()

    def execute(self):
        """执行临时模式"""
        # 获取要选择的人数
        while True:
            count_input = input("请输入要选择的人数（默认1）：").strip()
            if count_input == '':
                count = 1
                break
            try:
                count = int(count_input)
                if count > 0:
                    break
                else:
                    print("请输入正整数。")
            except ValueError:
                print("请输入有效的数字。")

        # 使用副本，不修改原文件
        df_copy = self.manager.get_copy()
        if df_copy is None:
            print("无法加载人员数据")
            return

        # 获取未选择的人员（如果有选择状态）
        if '是否已选' in df_copy.columns:
            unselected_df = df_copy[df_copy['是否已选'] == '否']
            # 如果有已选人员，也包含在可选范围内（临时模式忽略选择状态）
            if unselected_df.empty:
                unselected_df = df_copy.copy()
        else:
            unselected_df = df_copy.copy()

        if not unselected_df.empty:
            # 限制选择人数不超过总人数
            actual_count = min(count, len(unselected_df))

            # 从人员中随机选择
            if actual_count == 1:
                selected_rows = unselected_df.sample(n=1)
            else:
                selected_rows = unselected_df.sample(n=actual_count)

            # 输出信息
            self.display_manager.display_selection_result(selected_rows, "临时模式", actual_count)
            print(f"\n提示：此为临时选择，未保存到原文件")
        else:
            print("\n" + "=" * 50)
            print("人员名单为空！")
            print("=" * 50)


class MoppingMode:
    """拖地模式类"""

    def __init__(self, manager: PersonnelManager):
        self.manager = manager
        self.display_manager = DisplayManager()

    def execute(self):
        """执行拖地模式"""
        # 确保选择标记列存在
        self.manager.ensure_selection_columns()

        # 获取未选择的人员数量
        unselected_count = self.manager.get_unselected_count()

        try:
            if unselected_count >= 3:
                # 从未选择的人员中随机选择3名
                unselected_df = self.manager.get_unselected_personnel()
                if unselected_df is None:
                    print("无法获取未选择的人员数据")
                    return
                selected_rows = unselected_df.sample(n=3)

                # 更新选择状态
                indices = selected_rows.index
                self.manager.update_selection_status(indices, selected=True)

                # 保存数据
                self.manager.save_data()

                # 输出信息
                self.display_manager.display_selection_result(selected_rows, "拖地模式", 3)
                print("\n提示：这3名人员已被标记为已选，并已在原文件中更新")

            else:
                # 剩余人员不足3名
                print("\n" + "=" * 50)
                print(f"拖地模式 - 剩余人员不足3名（剩余{unselected_count}名）")
                print("=" * 50)

                if unselected_count > 0:
                    # 仍然可以选择剩余的人员
                    unselected_df = self.manager.get_unselected_personnel()
                    if unselected_df is None:
                        print("无法获取未选择的人员数据")
                        return
                    selected_rows = unselected_df.sample(n=unselected_count)

                    # 更新选择状态
                    indices = selected_rows.index
                    self.manager.update_selection_status(indices, selected=True)

                    # 保存数据
                    self.manager.save_data()

                    # 输出信息
                    print(f"\n已选择剩余的{unselected_count}名人员：")
                    print("-" * 50)
                    self.display_manager.display_selection_result(selected_rows, "拖地模式", unselected_count)
                    print("\n提示：所有人员都已被选择过！")
                else:
                    print("所有人员都已被选择过！")
                    print("如需重新开始，请选择'4. 清空名单记录'选项")

        except Exception as e:
            print(f"处理人员名单时发生错误：{str(e)}")


class RecordManager:
    """记录管理类"""

    def __init__(self, manager: PersonnelManager):
        self.manager = manager

    def execute(self):
        """执行清空记录操作"""
        try:
            # 检查是否有选择标记列
            if self.manager.df is None or '是否已选' not in self.manager.df.columns:
                print("提示：文件中没有选择记录需要清空")
                return

            # 检查是否有人员被选中
            selected_count = (self.manager.df['是否已选'] == '是').sum()
            if selected_count == 0:
                print("提示：没有人员被选中，无需清空")
                return

            # 清空选择记录
            self.manager.clear_selection_records()

            # 保存数据
            self.manager.save_data()

            # 输出信息
            print("\n" + "=" * 50)
            print("清空名单记录完成！")
            print("=" * 50)
            print(f"已重置 {selected_count} 名人员的选择状态")
            print("现在所有人员都可以被重新选择")
            print("=" * 50)

        except Exception as e:
            print(f"清空名单记录时发生错误：{str(e)}")


class RandomSelectorApp:
    """随机选择人员应用程序主类"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.excel_file = self.data_dir / "PersonnelList.xlsx"
        self.personnel_manager = PersonnelManager(self.excel_file)
        self.temporary_mode = TemporaryMode(self.personnel_manager)
        self.mopping_mode = MoppingMode(self.personnel_manager)
        self.record_manager = RecordManager(self.personnel_manager)

    def run(self):
        """运行应用程序"""
        print("随机选择人员程序")
        print("-" * 30)

        while True:
            print("\n" + "=" * 50)
            print("请选择模式：")
            print("=" * 50)
            print("1. 临时模式（可指定人数，不保存状态）")
            print("2. 拖地模式（选择3人，保存状态）")
            print("3. 清空名单记录")
            print("4. 退出程序")
            print("=" * 50)

            choice = input("请输入选项编号（1/2/3/4）：").strip()

            if choice == '1':
                print("\n正在使用临时模式...")
                if self.personnel_manager.load_data():
                    self.temporary_mode.execute()
                break
            elif choice == '2':
                print("\n正在使用拖地模式...")
                if self.personnel_manager.load_data():
                    self.mopping_mode.execute()
                break
            elif choice == '3':
                print("\n正在清空名单记录...")
                if self.personnel_manager.load_data():
                    self.record_manager.execute()
                break
            elif choice == '4':
                print("\n程序已退出。")
                break
            else:
                print("无效的选项，请重新输入。")


if __name__ == "__main__":
    app = RandomSelectorApp()
    app.run()
