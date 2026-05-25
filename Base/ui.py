import os
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeView, QProgressBar, QPushButton,
                             QFileDialog, QLabel, QHeaderView, QTabWidget, QTableWidget, QTableWidgetItem)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# Импорт функций из kerl.py
from kerl import get_tree, get_files_sorted_by_extension, count_items


class NumericSortItem(QStandardItem):
    """Кастомный элемент для правильной сортировки размеров в QTreeView"""
    def __init__(self, display_text, sort_value):
        super().__init__(display_text)
        self.setData(sort_value, Qt.ItemDataRole.UserRole)

    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)


# Поток сканирования с поддержкой реального прогресса
class ScanThread(QThread):
    count_finished = pyqtSignal(int)  # Сигнал передачи общего числа файлов
    progress = pyqtSignal(str, int)   # Текущий путь, текущее количество обработанных файлов
    finished = pyqtSignal(dict)       # Итоговое дерево

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def run(self):
        # Шаг 1: Быстрый предподсчет общего числа элементов для прогресс-бара
        total_items = count_items(self.root_path)
        self.count_finished.emit(total_items)

        # Шаг 2: Запуск основного сканирования с передачей счетчика прогресса
        tree = get_tree(
            self.root_path,
            progress_callback=lambda path, count: self.progress.emit(path, count)
        )
        self.finished.emit(tree)


class DiskUsageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Space Analyzer")
        self.resize(1100, 750)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Панель управления
        self.top_panel = QHBoxLayout()
        self.btn_scan = QPushButton("Выбрать папку")
        self.btn_scan.setFixedWidth(150)
        self.btn_scan.clicked.connect(self.start_scan)

        self.lbl_status = QLabel("Готов к работе")
        self.top_panel.addWidget(self.btn_scan)
        self.top_panel.addWidget(self.lbl_status)
        self.layout.addLayout(self.top_panel)

        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        # Вкладки
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Вкладка 1: Дерево каталогов
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Имя", "Размер", "Тип", "Владелец", "Файлов"])
        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.tabs.addTab(self.tree_view, "Структура каталогов")

        # Вкладка 2: Расширения
        self.ext_table = QTableWidget()
        self.ext_table.setColumnCount(3)
        self.ext_table.setHorizontalHeaderLabels(["Расширение", "Количество файлов", "Общий размер"])
        self.ext_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ext_table.setSortingEnabled(True)
        self.tabs.addTab(self.ext_table, "Типы файлов (Расширения)")

    def start_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для анализа")
        if folder:
            self.model.removeRows(0, self.model.rowCount())
            self.ext_table.setRowCount(0)

            # Настраиваем прогресс-бар на старт
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Подготовка к сканированию (подсчет файлов)...")
            self.btn_scan.setEnabled(False)
            self.tree_view.setSortingEnabled(False)

            # Инициализация потока
            self.scan_thread = ScanThread(folder)
            self.scan_thread.count_finished.connect(self.setup_progress_bar)
            self.scan_thread.progress.connect(self.update_progress)
            self.scan_thread.finished.connect(self.display_data)
            self.scan_thread.start()

    def setup_progress_bar(self, total_items):
        """Вызывается, когда предварительный подсчет завершен"""
        self.progress_bar.setMaximum(total_items)
        self.progress_bar.setFormat("%p% (%v / %m)")

    def update_progress(self, path, current_count):
        """Обновление прогресс-бара и текста статуса в реальном времени"""
        # Безопасное ограничение, если во время сканирования добавились новые файлы
        if current_count > self.progress_bar.maximum():
            self.progress_bar.setMaximum(current_count + 100)

        self.progress_bar.setValue(current_count)

        if len(path) > 60:
            path = "..." + path[-57:]
        self.lbl_status.setText(f"Сканирую: {path}")

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def display_data(self, data):
        # Завершение работы прогресс-бара
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%")
        self.lbl_status.setText(f"Сканирование завершено. Общий размер: {self.format_size(data['size'])}")
        self.btn_scan.setEnabled(True)

        self.tree_view.setUpdatesEnabled(False)
        self.populate_tree_iterative(data)
        self.tree_view.expandToDepth(0)

        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.tree_view.setUpdatesEnabled(True)

        self.populate_extensions_tab(data)

    def populate_tree_iterative(self, root_data):
        root_item = self.model.invisibleRootItem()
        stack = [(root_item, root_data)]

        while stack:
            parent_item, node_data = stack.pop()

            name_item = QStandardItem(node_data["name"])
            size_item = NumericSortItem(self.format_size(node_data["size"]), node_data["size"])

            node_type = node_data.get("type", "directory")
            type_item = QStandardItem("Папка" if node_type == "directory" else "Файл")

            owner_item = QStandardItem(node_data.get("owner", "User"))

            count_val = node_data.get("count", 0) if node_type == "directory" else 0
            count_item = NumericSortItem(str(count_val) if count_val else "", count_val)

            parent_item.appendRow([name_item, size_item, type_item, owner_item, count_item])

            if "children" in node_data and node_data["children"]:
                for child in node_data["children"].values():
                    stack.append((name_item, child))

    def populate_extensions_tab(self, root_data):
        ext_data = get_files_sorted_by_extension(root_data)

        self.ext_table.setSortingEnabled(False)
        self.ext_table.setRowCount(len(ext_data))

        for row, (ext, files) in enumerate(ext_data.items()):
            ext_name = ext if ext else "[Без расширения]"
            total_size = sum(f['size'] for f in files)
            count = len(files)

            item_ext = QTableWidgetItem(ext_name)

            item_count = QTableWidgetItem()
            item_count.setData(Qt.ItemDataRole.EditRole, count)

            class TableNumItem(QTableWidgetItem):
                def __lt__(self, other):
                    return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)

            item_size_custom = TableNumItem(self.format_size(total_size))
            item_size_custom.setData(Qt.ItemDataRole.UserRole, total_size)

            self.ext_table.setItem(row, 0, item_ext)
            self.ext_table.setItem(row, 1, item_count)
            self.ext_table.setItem(row, 2, item_size_custom)

        self.ext_table.setSortingEnabled(True)
        self.ext_table.sortByColumn(2, Qt.SortOrder.DescendingOrder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiskUsageApp()
    window.show()
    sys.exit(app.exec())