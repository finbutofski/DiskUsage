import os
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeView, QProgressBar, QPushButton,
                             QFileDialog, QLabel, QHeaderView)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# 1. Поток сканирования (чтобы UI не лагал)
class ScanThread(QThread):
    progress = pyqtSignal(str, int)  # Имя текущей папки, текущий размер
    finished = pyqtSignal(dict)

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def run(self):
        # Здесь ваша логика get_tree, но с отправкой сигналов
        result = self.scan(self.root_path)
        self.finished.emit(result)

    def scan(self, path):
        # Упрощенная версия для примера
        tree_data = {"name": path, "size": 0, "children": []}
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                    tree_data["size"] += size
                    tree_data["children"].append({"name": entry.name, "size": size, "type": "file"})
                elif entry.is_dir(follow_symlinks=False):
                    self.progress.emit(entry.path, 0)
                    subdir = self.scan(entry.path)
                    tree_data["size"] += subdir["size"]
                    tree_data["children"].append(subdir)
        except PermissionError:
            pass
        return tree_data

# 2. Главное окно
class DiskUsageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Disk Usage Analyzer")
        self.resize(1000, 700)

        # UI элементы
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Верхняя панель
        self.top_panel = QHBoxLayout()
        self.btn_scan = QPushButton("Выбрать папку")
        self.btn_scan.clicked.connect(self.start_scan)
        self.lbl_status = QLabel("Готов к работе")
        self.top_panel.addWidget(self.btn_scan)
        self.top_panel.addWidget(self.lbl_status)
        self.layout.addLayout(self.top_panel)

        # Прогрессбар
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)

        # Дерево (Таблица)
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Имя", "Размер", "Тип", "Владелец"])
        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.tree_view)

    def start_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.model.clear()
            self.model.setHorizontalHeaderLabels(["Имя", "Размер", "Тип", "Владелец"])
            self.progress_bar.setRange(0, 0) # Анимация "загрузки"
            self.scan_thread = ScanThread(folder)
            self.scan_thread.progress.connect(self.update_status)
            self.scan_thread.finished.connect(self.display_data)
            self.scan_thread.start()

    def update_status(self, path, size):
        self.lbl_status.setText(f"Сканирую: {path[:50]}...")

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024

    def display_data(self, data):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Сканирование завершено")

        # Добавление данных в дерево (рекурсивно)
        root_item = self.add_node(self.model.invisibleRootItem(), data)
        self.tree_view.expandToDepth(0)

    def add_node(self, parent_item, node_data):
        name_item = QStandardItem(node_data["name"])
        size_item = QStandardItem(self.format_size(node_data["size"]))
        type_item = QStandardItem(node_data.get("type", "directory"))

        parent_item.appendRow([name_item, size_item, type_item])

        if "children" in node_data:
            for child in node_data["children"]:
                self.add_node(name_item, child)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiskUsageApp()
    window.show()
    sys.exit(app.exec())