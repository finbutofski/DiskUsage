from datetime import datetime, timedelta
from PyQt6.QtCore import QSortFilterProxyModel, QModelIndex, Qt


class DiskFilterProxyModel(QSortFilterProxyModel):
    """
    Прокси-модель, которая фильтрует элементы QStandardItemModel
    по расширению, размеру, времени, владельцу и глубине.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ext_filter = ""  # Пример: "png, jpg"
        self.size_min = 0  # В байтах
        self.size_max = float('inf')  # В байтах
        self.time_days = None  # Число дней (None = за все время)
        self.owner_filter = ""  # Имя пользователя
        self.max_depth = None  # Макс. (None = без ограничений)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Метод вызывается PyQt для каждой строки дерева/списка.
        Если возвращает True — строка видна, если False — скрыта.
        """
        model = self.sourceModel()

        idx_name = model.index(source_row, 0, source_parent)
        idx_size = model.index(source_row, 1, source_parent)
        idx_type = model.index(source_row, 2, source_parent)
        idx_owner = model.index(source_row, 3, source_parent)

        if self.max_depth is not None:
            depth = 0
            curr = source_parent
            while curr.isValid():
                depth += 1
                curr = curr.parent()
            if depth >= self.max_depth:
                return False

        # Данные из элементов
        name = model.data(idx_name) or ""
        type_str = model.data(idx_type) or ""
        is_dir = "Папка" in type_str

        size_bytes = model.data(idx_size, Qt.ItemDataRole.UserRole) or 0


        if is_dir:
            child_count = model.rowCount(idx_name)
            for i in range(child_count):
                if self.filterAcceptsRow(i, idx_name):
                    return True

            return self.size_min <= size_bytes <= self.size_max

        if self.ext_filter:
            valid_exts = [e.strip().lower().lstrip('.') for e in self.ext_filter.split(',') if e.strip()]
            file_ext = name.split('.')[-1].lower() if '.' in name else ""
            if valid_exts and (file_ext not in valid_exts):
                return False

        if not (self.size_min <= size_bytes <= self.size_max):
            return False

        if self.owner_filter:
            owner = model.data(idx_owner) or ""
            if self.owner_filter.lower() not in owner.lower():
                return False

        if self.time_days is not None:
            mtime = model.data(idx_name, Qt.ItemDataRole.UserRole + 2)
            if mtime:
                cutoff_date = datetime.now() - timedelta(days=self.time_days)
                if datetime.fromtimestamp(mtime) < cutoff_date:
                    return False

        return True