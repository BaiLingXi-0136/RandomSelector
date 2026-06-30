import random
import pandas as pd
from pathlib import Path
from datetime import datetime

# 创建示例数据文件（如果不存在）
def create_sample_data():
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    if not excel_file.exists():
        # 创建示例数据
        sample_data = {
            '姓名': ['张三', '李四', '王五', '赵六', '钱七', '孙八', '周九', '吴十'],
            '部门': ['技术部', '销售部', '人事部', '财务部', '市场部', '研发部', '客服部', '运营部'],
            '职位': ['工程师', '销售经理', 'HR专员', '会计', '市场专员', '研发工程师', '客服代表', '运营主管']
        }

        df_sample = pd.DataFrame(sample_data)
        df_sample.to_excel(excel_file, index=False)
        print(f"已创建示例数据文件: {excel_file}")
        return True
    return False


def demo_temp_mode():
    """演示临时模式"""
    print("\n" + "=" * 60)
    print("演示：临时模式 - 单次抽选，不保存状态")
    print("=" * 60)

    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    # 获取未选择的人员（临时模式不关心之前的选择）
    unselected_df = df[df.get('是否已选', '否') == '否']

    if not unselected_df.empty:
        # 从未选择的人员中随机选择
        selected_row = unselected_df.sample(n=1)

        print("\n已选择的人员信息：")
        print("-" * 40)

        person_info = selected_row.iloc[0]

        # 遍历所有列，只显示有值的列
        for col, value in person_info.items():
            if pd.notna(value):
                print(f"{col}: {value}")

        print(f"\n注意：此为临时选择，未保存到原文件")
    else:
        print("所有人员都已被选择过！")


def demo_mopping_mode():
    """演示拖地模式"""
    print("\n" + "=" * 60)
    print("演示：拖地模式 - 选择3人，保存状态")
    print("=" * 60)

    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    # 检查是否已经有选择标记列
    if '是否已选' not in df.columns:
        # 添加选择标记列
        df['是否已选'] = '否'
        print("已添加'是否已选'列到人员名单中")

    # 获取未选择的人员数量
    unselected_count = (df['是否已选'] == '否').sum()

    if unselected_count >= 3:
        # 从未选择的人员中随机选择3名
        unselected_df = df[df['是否已选'] == '否']
        selected_rows = unselected_df.sample(n=3)

        # 更新选择状态
        for idx in selected_rows.index:
            df.at[idx, '是否已选'] = '是'
            df.at[idx, '选择时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # 保存更新后的Excel文件
        df.to_excel(excel_file, index=False)

        # 输出信息
        print("\n已选择的3名人员信息：")
        print("-" * 40)

        for i, (_, row) in enumerate(selected_rows.iterrows(), 1):
            print(f"\n人员 {i}:")
            print("-" * 30)

            person_info = row
            # 遍历所有列（除了选择状态列），只显示有值的列
            for col, value in person_info.items():
                if col != '是否已选' and pd.notna(value):
                    print(f"{col}: {value}")

            print(f"是否已选: 是")
            print(f"选择时间: {person_info.get('选择时间', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")

        print("\n提示：这3名人员已被标记为已选，并已在原文件中更新")
    else:
        print(f"剩余人员不足3名（剩余{unselected_count}名）")


def show_current_status():
    """显示当前选择状态"""
    print("\n" + "=" * 60)
    print("当前选择状态")
    print("=" * 60)

    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    if '是否已选' in df.columns:
        selected_count = (df['是否已选'] == '是').sum()
        total_count = len(df)
        print(f"已选择：{selected_count}人")
        print(f"剩余：{total_count - selected_count}人")
        print(f"总计：{total_count}人")

        # 显示已选择的人员
        selected_df = df[df['是否已选'] == '是']
        if not selected_df.empty:
            print("\n已选择的人员名单：")
            for _, row in selected_df.iterrows():
                print(f"- {row['姓名']} ({row['部门']})")
    else:
        print("尚未有任何人员被选择")


def reset_selection():
    """重置选择状态"""
    print("\n" + "=" * 60)
    print("重置选择状态")
    print("=" * 60)

    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 读取Excel文件
    df = pd.read_excel(excel_file)

    if '是否已选' in df.columns:
        # 重置所有选择状态
        df['是否已选'] = '否'
        if '选择时间' in df.columns:
            df = df.drop('选择时间', axis=1)

        # 保存重置后的Excel文件
        df.to_excel(excel_file, index=False)
        print("已重置所有人员的选择状态")
    else:
        print("没有需要重置的选择状态")


if __name__ == "__main__":
    print("随机选择人员程序 - 自动演示模式")
    print("-" * 60)

    # 创建示例数据
    create_sample_data()

    # 显示初始状态
    print("\n初始状态：")
    show_current_status()

    # 演示临时模式
    demo_temp_mode()

    # 演示拖地模式
    demo_mopping_mode()

    # 显示选择后的状态
    show_current_status()

    # 重置状态
    reset_selection()

    # 显示最终状态
    show_current_status()

    print("\n演示完成！")
    print("\n使用说明：")
    print("1. 临时模式：单次抽选，不保存状态，程序退出后选择记录消失")
    print("2. 拖地模式：每次选择3人，保存状态到Excel文件")
    print("3. 程序会自动创建示例数据文件（如果不存在）")