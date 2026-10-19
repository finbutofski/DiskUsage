from PyQt6.QtCore import Qt
from PyQt6.QtGui import QStandardItem
from PyQt6.QtWidgets import QTableWidgetItem

SORT_ROLE = Qt.ItemDataRole.UserRole


class NumericSortItem(QStandardItem):
    """Элемент модели дерева: показывает текст, сортируется по числу."""

    def __init__(self, display_text: str, sort_value):
        super().__init__(display_text)
        self.setData(sort_value, SORT_ROLE)

    def __lt__(self, other):
        return self.data(SORT_ROLE) < other.data(SORT_ROLE)


class NumericTableItem(QTableWidgetItem):
    """То же самое для QTableWidget."""

    def __init__(self, display_text: str, sort_value):
        super().__init__(display_text)
        self.setData(SORT_ROLE, sort_value)

    def __lt__(self, other):
        return self.data(SORT_ROLE) < other.data(SORT_ROLE)
