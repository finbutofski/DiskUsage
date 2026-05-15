import os
import sys
import time
from Base.kerl import get_tree
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeView, QProgressBar, QPushButton,
                             QFileDialog, QLabel, QHeaderView)
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import QThread, pyqtSignal
from pathlib import Path


# 1. Поток сканирования
class ScanThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(dict)

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def run(self):
        tree = get_tree(
            self.root_path,
            progress_callback=lambda path: self.progress.emit(path, 0)
        )
        self.finished.emit(tree)


# 2. Главное окно
class DiskUsageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python Disk Usage Analyzer")
        self.resize(1000, 700)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.top_panel = QHBoxLayout()
        self.btn_scan = QPushButton("Выбрать папку")
        self.btn_scan.clicked.connect(self.start_scan)
        self.lbl_status = QLabel("Готов к работе")
        self.top_panel.addWidget(self.btn_scan)
        self.top_panel.addWidget(self.lbl_status)
        self.layout.addLayout(self.top_panel)

        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)

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
            self.progress_bar.setRange(0, 0)
            self.btn_scan.setEnabled(False)

            self.scan_thread = ScanThread(folder)
            self.scan_thread.progress.connect(self.update_status)
            self.scan_thread.finished.connect(self.display_data)
            self.scan_thread.start()

    def update_status(self, path, size):
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
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Сканирование завершено")
        self.btn_scan.setEnabled(True)

        self.tree_view.setUpdatesEnabled(False)

        # Вызываем новый безопасный метод заполнения
        self.populate_tree_iterative(data)
        self.tree_view.expandToDepth(0)

        self.tree_view.setUpdatesEnabled(True)

    def populate_tree_iterative(self, root_data):
        """Заполнение дерева БЕЗ рекурсии и без сортировки"""
        root_item = self.model.invisibleRootItem()
        stack = [(root_item, root_data)]

        while stack:
            parent_item, node_data = stack.pop()

            name_item = QStandardItem(node_data["name"])
            size_item = QStandardItem(self.format_size(node_data["size"]))

            node_type = node_data.get("type", "directory")
            type_item = QStandardItem("Папка" if node_type == "directory" else "Файл")
            owner = node_data.get("owner", "User")
            owner_item = QStandardItem(owner)
            parent_item.appendRow([name_item, size_item, type_item, owner_item])
            if "children" in node_data and node_data["children"]:
                children_list = list(node_data["children"].values())

                for child in reversed(children_list):
                    stack.append((name_item, child))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiskUsageApp()
    window.show()
    sys.exit(app.exec())