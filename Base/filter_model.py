import os
from datetime import datetime, timedelta
from PyQt6.QtCore import QSortFilterProxyModel, QModelIndex, Qt


class DiskFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ext_filter = ""
        self.size_min = 0
        self.size_max = float('inf')
        self.time_days = None
        self.owner_filter = ""
        self.max_depth = None

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model = self.sourceModel()

        idx_name = model.index(source_row, 0, source_parent)
        idx_size = model.index(source_row, 1, source_parent)
        idx_type = model.index(source_row, 2, source_parent)
        idx_owner = model.index(source_row, 3, source_parent)

        # 1. Проверка глубины
        if self.max_depth is not None:
            depth = 0
            curr = source_parent
            while curr.isValid():
                depth += 1
                curr = curr.parent()
            if depth >= self.max_depth:
                return False

        name = model.data(idx_name) or ""
        type_str = model.data(idx_type) or ""
        is_dir = "Папка" in type_str
        size_bytes = model.data(idx_size, Qt.ItemDataRole.UserRole) or 0

        # 2. Если это ПАПКА: показываем её только если ХОТЯ БЫ ОДИН из её потомков подходить под фильтр
        if is_dir:
            child_count = model.rowCount(idx_name)
            if child_count == 0:
                # Пустая папка
                return (not self.ext_filter) and (self.size_min <= size_bytes <= self.size_max)

            # Проверяем всех дочерних элементов папки
            for i in range(child_count):
                if self.filterAcceptsRow(i, idx_name):
                    return True
            return False

        # 3. Если это ФАЙЛ:

        # Расширение
        if self.ext_filter:
            valid_exts = [e.strip().lower().lstrip('.') for e in self.ext_filter.split(',') if e.strip()]
            file_ext = name.split('.')[-1].lower() if '.' in name else ""
            if valid_exts and (file_ext not in valid_exts):
                return False

        # Размер
        if not (self.size_min <= size_bytes <= self.size_max):
            return False

        # Владелец
        if self.owner_filter:
            owner = model.data(idx_owner) or ""
            if self.owner_filter.lower() not in owner.lower():
                return False

        # Время
        if self.time_days is not None:
            mtime = model.data(idx_name, Qt.ItemDataRole.UserRole + 2)
            if mtime:
                cutoff_date = datetime.now() - timedelta(days=self.time_days)
                if datetime.fromtimestamp(mtime) < cutoff_date:
                    return False

        return True