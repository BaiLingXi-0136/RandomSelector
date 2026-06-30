import pandas as pd
from pathlib import Path
from datetime import datetime


def select_personnel_single():
    """
    临时模式：从PersonnelList.xlsx中随机选择一名人员并输出相关信息
    确保单次运行时选择不同的人员，程序结束后不保存状态
    """
    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 检查文件是否存在
    if not excel_file.exists():
        print(f"错误：找不到人员名单文件 {excel_file}")
        return

    # 读取Excel文件
    try:
        # 读取Excel文件，保留所有列
        df = pd.read_excel(excel_file)

        # 检查是否有数据
        if df.empty:
            print("错误：人员名单文件为空")
            return

        # 获取所有人员姓名
        if '姓名' not in df.columns:
            print("错误：人员名单中必须有'姓名'列")
            return

        # 临时模式：使用副本，不修改原文件
        df_copy = df.copy()

        # 获取未选择的人员
        unselected_df = df_copy[df_copy['是否已选'] == '否']

        if not unselected_df.empty:
            # 从未选择的人员中随机选择
            selected_row = unselected_df.sample(n=1)

            # 输出信息
            print("\n" + "=" * 50)
            print("临时模式 - 已选择的人员信息：")
            print("=" * 50)

            person_info = selected_row.iloc[0]

            # 遍历所有列，只显示有值的列
            for col, value in person_info.items():
                if pd.notna(value):
                    print(f"{col}: {value}")

            print(f"\n提示：此为临时选择，未保存到原文件")
        else:
            print("\n" + "=" * 50)
            print("所有人员都已被选择过！")
            print("=" * 50)

    except Exception as e:
        print(f"处理人员名单时发生错误：{str(e)}")


def select_personnel_mopping():
    """
    拖地模式：从PersonnelList.xlsx中随机选择三名不重复人员并输出相关信息
    确保每次选择不同的人员，在原Excel文件中记录选择状态和时间
    """
    # 获取文件路径
    data_dir = Path("data")
    excel_file = data_dir / "PersonnelList.xlsx"

    # 检查文件是否存在
    if not excel_file.exists():
        print(f"错误：找不到人员名单文件 {excel_file}")
        return

    # 读取Excel文件
    try:
        # 读取Excel文件，保留所有列
        df = pd.read_excel(excel_file)

        # 检查是否有数据
        if df.empty:
            print("错误：人员名单文件为空")
            return

        # 获取所有人员姓名
        if '姓名' not in df.columns:
            print("错误：人员名单中必须有'姓名'列")
            return

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
            print("\n" + "=" * 50)
            print("拖地模式 - 已选择的3名人员信息：")
            print("=" * 50)

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
            # 剩余人员不足3名，可选择重置或提示
            print("\n" + "=" * 50)
            print(f"拖地模式 - 剩余人员不足3名（剩余{unselected_count}名）")
            print("=" * 50)

            if unselected_count > 0:
                # 仍然可以选择剩余的人员
                unselected_df = df[df['是否已选'] == '否']
                selected_rows = unselected_df.sample(n=unselected_count)

                # 更新选择状态
                for idx in selected_rows.index:
                    df.at[idx, '是否已选'] = '是'
                    df.at[idx, '选择时间'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 保存更新后的Excel文件
                df.to_excel(excel_file, index=False)

                # 输出信息
                print(f"\n已选择剩余的{unselected_count}名人员：")
                print("-" * 50)

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

                print("\n提示：所有人员都已被选择过！")
            else:
                print("所有人员都已被选择过！")
                print("如需重新开始，请手动清除Excel文件中的'是否已选'列")

    except Exception as e:
        print(f"处理人员名单时发生错误：{str(e)}")


if __name__ == "__main__":
    print("随机选择人员程序")
    print("-" * 30)

    # 运行交互式选择
    while True:
        print("\n" + "=" * 50)
        print("请选择模式：")
        print("=" * 50)
        print("1. 临时模式（单次抽选，不保存状态）")
        print("2. 拖地模式（选择3人，保存状态）")
        print("3. 退出程序")
        print("=" * 50)

        choice = input("请输入选项编号（1/2/3）：").strip()

        if choice == '1':
            print("\n正在使用临时模式...")
            select_personnel_single()
            break
        elif choice == '2':
            print("\n正在使用拖地模式...")
            select_personnel_mopping()
            break
        elif choice == '3':
            print("\n程序已退出。")
            break
        else:
            print("无效的选项，请重新输入。")
