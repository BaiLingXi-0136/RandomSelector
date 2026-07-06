"""UI 辅助函数与组件构建器"""
import flet as ft
import pandas as pd
from config import RESOURCE_DIR


# ==================== 通用工具 ====================

def safe_val(val):
    """安全获取单元格值，NaN转为空字符串"""
    return str(val) if pd.notna(val) else ""


def not_implemented(message):
    """终端提示未完成的功能"""
    print(f"[未完成] {message}")


# ==================== 菜单项构建 ====================

def menu_item(label, shortcut="", icon=None, on_click=None, disabled=False):
    """构建标准菜单项，含标签、快捷键提示和图标"""
    row_children = [ft.Text(label)]
    if shortcut:
        row_children.append(
            ft.Text(shortcut, style=ft.TextStyle(color="#999999", size=12))
        )
    return ft.MenuItemButton(
        content=ft.Row(row_children, expand=True),
        leading=icon,
        on_click=on_click,
        disabled=disabled,
    )


# ==================== 对话框 ====================

def show_about_dialog(e):
    """打开关于对话框，内容从 ABOUT.md 读取"""
    page = e.page
    about_path = RESOURCE_DIR / "config" / "ABOUT.md"
    try:
        about_text = about_path.read_text(encoding="utf-8")
    except (OSError,):
        about_text = "无法加载关于信息"

    dialog = ft.AlertDialog(
        title=ft.Text("关于"),
        content=ft.Container(
            ft.Markdown(
                about_text,
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            ),
            width=500,
        ),
        actions=[
            ft.TextButton("确定", on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


def show_help_dialog(e):
    """打开使用说明对话框，内容从 README.md 读取"""
    page = e.page
    readme_path = RESOURCE_DIR / "README.md"
    try:
        help_text = readme_path.read_text(encoding="utf-8")
    except (OSError,):
        help_text = "无法加载使用说明"

    dialog = ft.AlertDialog(
        title=ft.Text("使用说明"),
        content=ft.Column(
            [
                ft.Markdown(
                    help_text,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
            ],
            scroll=ft.ScrollMode.AUTO,
            width=700,
            height=450,
        ),
        actions=[
            ft.TextButton("确定", on_click=lambda _: page.close(dialog)),
        ],
    )
    page.open(dialog)


# ==================== 表格构建 ====================

def make_selection_table():
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


def make_row_cells(i, row):
    """构建一行的DataCell列表"""
    return [
        ft.DataCell(ft.Text(str(i), size=13, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['姓名']), size=13)),
        ft.DataCell(ft.Text(safe_val(row['学号']), size=13, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['班级']), size=13, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['性别']), size=13, text_align=ft.TextAlign.CENTER)),
    ]


def build_personnel_table(df, include_status=True, start_index=1):
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
            ft.DataCell(ft.Text(safe_val(row['姓名']), size=13)),
            ft.DataCell(ft.Text(safe_val(row['学号']), size=13, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['班级']), size=13, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['性别']), size=13, text_align=ft.TextAlign.CENTER)),
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


def build_split_personnel_tables(df, include_status=True):
    """将数据对半拆分，返回左右两个表格平铺的Row"""
    mid = (len(df) + 1) // 2  # 向上取整，左表多一个

    left_df = df.iloc[:mid]
    right_df = df.iloc[mid:]

    left_table = build_personnel_table(left_df, include_status, start_index=1)
    right_table = build_personnel_table(
        right_df, include_status, start_index=mid + 1
    ) if len(right_df) > 0 else None

    tables = [
        ft.Column([left_table], expand=True, scroll=ft.ScrollMode.AUTO),
    ]
    if right_table is not None:
        tables.append(ft.VerticalDivider(width=1, color="#e0e0e0"))
        tables.append(ft.Column([right_table], expand=True, scroll=ft.ScrollMode.AUTO))

    return ft.Row(tables, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
