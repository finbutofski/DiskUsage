from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from tree_builder import get_files_sorted_by_extension

from .items import NumericTableItem
from .utils import format_size


class ExtensionsPanel(QWidget):
    """Таблица: расширение / количество / общий размер."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Расширение", "Количество файлов", "Общий размер"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSortingEnabled(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Типы файлов (Расширения)"))
        layout.addWidget(self.table, stretch=1)

    def clear(self) -> None:
        self.table.setRowCount(0)

    def load(self, root_data: dict) -> None:
        ext_data = get_files_sorted_by_extension(root_data)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(ext_data))

        for row, (ext, files) in enumerate(ext_data.items()):
            total_size = sum(f["size"] for f in files)

            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.EditRole, len(files))

            self.table.setItem(row, 0, QTableWidgetItem(ext or "[Без расширения]"))
            self.table.setItem(row, 1, count_item)
            self.table.setItem(row, 2, NumericTableItem(format_size(total_size), total_size))

        self.table.setSortingEnabled(True)
        self.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
