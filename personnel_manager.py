"""人员数据管理"""
import pandas as pd
from datetime import datetime
from pathlib import Path
from config import get_data_file_path, save_settings


class PersonnelManager:
    def __init__(self, file_path=None):
        self.df = None
        self.file_path = Path(file_path) if file_path else get_data_file_path()

    def set_file_path(self, path):
        """更换数据文件路径"""
        self.file_path = Path(path)
        self.df = None
        save_settings({"data_file": str(self.file_path.resolve())})

    @property
    def file_name(self) -> str:
        """返回当前数据文件的简短名称"""
        return self.file_path.name

    def load_data(self) -> bool:
        """加载人员数据"""
        try:
            if not self.file_path.exists():
                return False
            self.df = pd.read_excel(self.file_path)
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
        except Exception:
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
            self.df.to_excel(self.file_path, index=False)

    def clear_selection_records(self):
        """清空选择记录"""
        if self.df is not None:
            self.df['是否已选'] = '否'
            self.df['选择时间'] = ''
