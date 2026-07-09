"""UI 辅助函数与组件构建器"""
import flet as ft
import pandas as pd

from constants import (
    COLOR_BORDER, COLOR_DANGER, COLOR_PRIMARY,
    COLOR_ROW_ALT, COLOR_ROW_SELECTED, COLOR_TABLE_HEADER,
    FONT_SIZE_SMALL,
    TABLE_COLUMN_SPACING, TABLE_HEADING_ROW_HEIGHT,
    TABLE_DATA_ROW_MIN_HEIGHT, TABLE_DATA_ROW_MAX_HEIGHT,
)

_FW_BOLD = ft.FontWeight.BOLD


# ==================== 通用工具 ====================

def safe_val(val):
    """安全获取单元格值，NaN转为空字符串"""
    return str(val) if pd.notna(val) else ""


# ==================== 菜单项构建 ====================

def menu_item(label: str, shortcut: str = "", icon=None,
              on_click=None, disabled: bool = False):
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


# ==================== 表格构建 ====================

def make_selection_table() -> ft.DataTable:
    """创建抽选结果用的空DataTable（不含是否已选列）"""
    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("序号", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
            ft.DataColumn(ft.Text("姓名", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
            ft.DataColumn(ft.Text("学号", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
            ft.DataColumn(ft.Text("班级", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
            ft.DataColumn(ft.Text("性别", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
        ],
        rows=[],
        column_spacing=TABLE_COLUMN_SPACING,
        heading_row_height=TABLE_HEADING_ROW_HEIGHT,
        data_row_min_height=TABLE_DATA_ROW_MIN_HEIGHT,
        data_row_max_height=TABLE_DATA_ROW_MAX_HEIGHT,
        border=ft.border.all(color=COLOR_BORDER, width=1),
        border_radius=8,
        show_bottom_border=True,
        heading_row_color=COLOR_TABLE_HEADER,
    )


def make_row_cells(i: int, row) -> list:
    """构建一行的DataCell列表"""
    return [
        ft.DataCell(ft.Text(str(i), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['姓名']), size=FONT_SIZE_SMALL)),
        ft.DataCell(ft.Text(safe_val(row['学号']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['班级']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
        ft.DataCell(ft.Text(safe_val(row['性别']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
    ]


def build_personnel_table(df: pd.DataFrame, include_status: bool = True,
                          start_index: int = 1) -> ft.DataTable:
    """构建人员信息DataTable"""
    columns = [
        ft.DataColumn(ft.Text("序号", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
        ft.DataColumn(ft.Text("姓名", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
        ft.DataColumn(ft.Text("学号", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
        ft.DataColumn(ft.Text("班级", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
        ft.DataColumn(ft.Text("性别", weight=_FW_BOLD, size=FONT_SIZE_SMALL)),
    ]
    if include_status:
        columns.append(ft.DataColumn(ft.Text("是否已选", weight=_FW_BOLD, size=FONT_SIZE_SMALL)))

    table = ft.DataTable(
        columns=columns,
        rows=[],
        column_spacing=TABLE_COLUMN_SPACING,
        heading_row_height=TABLE_HEADING_ROW_HEIGHT,
        data_row_min_height=TABLE_DATA_ROW_MIN_HEIGHT,
        data_row_max_height=TABLE_DATA_ROW_MAX_HEIGHT,
        border=ft.border.all(color=COLOR_BORDER, width=1),
        border_radius=8,
        show_bottom_border=True,
        heading_row_color=COLOR_TABLE_HEADER,
    )

    for i, (_, row) in enumerate(df.iterrows(), start_index):
        selected = (include_status and row['是否已选'] == '是')

        cells = [
            ft.DataCell(ft.Text(str(i), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['姓名']), size=FONT_SIZE_SMALL)),
            ft.DataCell(ft.Text(safe_val(row['学号']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['班级']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
            ft.DataCell(ft.Text(safe_val(row['性别']), size=FONT_SIZE_SMALL, text_align=ft.TextAlign.CENTER)),
        ]

        if include_status:
            status_text = "是" if selected else "否"
            status_color = COLOR_PRIMARY if selected else COLOR_DANGER
            cells.append(
                ft.DataCell(ft.Text(
                    status_text, size=FONT_SIZE_SMALL, color=status_color,
                    weight=_FW_BOLD, text_align=ft.TextAlign.CENTER,
                ))
            )

        row_color = COLOR_ROW_SELECTED if selected else (
            COLOR_ROW_ALT if i % 2 == 0 else None
        )
        table.rows.append(ft.DataRow(cells=cells, color=row_color))

    return table


def build_split_personnel_tables(df: pd.DataFrame, include_status: bool = True) -> ft.Row:
    """将数据对半拆分，返回左右两个表格平铺的Row"""
    mid = (len(df) + 1) // 2

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
        tables.append(ft.VerticalDivider(width=1, color=COLOR_BORDER))
        tables.append(ft.Column([right_table], expand=True, scroll=ft.ScrollMode.AUTO))

    return ft.Row(tables, expand=True, vertical_alignment=ft.CrossAxisAlignment.START)
