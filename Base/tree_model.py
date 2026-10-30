"""Построение QStandardItemModel из дерева tree_builder."""
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QStandardItem, QStandardItemModel

from .items import NumericSortItem
from .utils import format_size

HEADERS = ["Имя", "Размер", "Тип", "Владелец", "Файлов"]

# Роли данных на элементе «Имя»
PATH_ROLE = Qt.ItemDataRole.UserRole + 1
MTIME_ROLE = Qt.ItemDataRole.UserRole + 2  # читает DiskFilterProxyModel

ADS_COLOR = QColor("teal")


def create_model() -> QStandardItemModel:
    model = QStandardItemModel()
    model.setHorizontalHeaderLabels(HEADERS)
    return model


def populate_model(model: QStandardItemModel, root_data: dict, root_path: str) -> None:
    """Итеративно (без рекурсии) заполняет модель."""
    stack = [(model.invisibleRootItem(), root_data, root_path)]

    while stack:
        parent_item, node, full_path = stack.pop()
        row = _make_row(node, full_path)
        parent_item.appendRow(row)

        name_item = row[0]
        for child in node.get("children", {}).values():
            stack.append((name_item, child, os.path.join(full_path, child["name"])))


def _make_row(node: dict, full_path: str) -> list:
    is_dir = node.get("type", "directory") == "directory"
    ads_size = node.get("ads_size", 0)

    name_item = QStandardItem(node["name"])
    name_item.setData(full_path, PATH_ROLE)
    name_item.setData(node.get("mtime"), MTIME_ROLE)

    size_item = NumericSortItem(format_size(node["size"]), node["size"])

    if is_dir:
        type_str = "Папка"
    else:
        type_str = "Файл (с ADS)" if ads_size > 0 else "Файл"
    type_item = QStandardItem(type_str)

    owner_item = QStandardItem(node.get("owner", "User"))

    count = node.get("count", 0) if is_dir else 0
    count_item = NumericSortItem(str(count) if count else "", count)

    # Подсвечиваем файлы с альтернативными потоками данных
    if ads_size > 0:
        type_item.setForeground(ADS_COLOR)
        name_item.setForeground(ADS_COLOR)
        name_item.setToolTip(f"Размер скрытых потоков (ADS): {format_size(ads_size)}")

    return [name_item, size_item, type_item, owner_item, count_item]
