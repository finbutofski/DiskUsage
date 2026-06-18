import os
import sys
import subprocess
import shutil
import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTreeView, QProgressBar, QPushButton,
                             QFileDialog, QLabel, QHeaderView, QTableWidget, QTableWidgetItem,
                             QMenu, QSplitter)
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QPainter, QColor, QFont, QPalette
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRect

# Импорт функций из kerl.py
from kerl import get_tree, get_files_sorted_by_extension, count_items


PALETTE = ["#4A90D9", "#5BA85A", "#E87C35", "#C94F4F", "#8B6BB1",
           "#3AADA8", "#E8C440", "#D96B8A", "#7FB3D3", "#95A5A6"]


def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"


class NumericSortItem(QStandardItem):
    """Кастомный элемент для правильной сортировки размеров в QTreeView"""
    def __init__(self, display_text, sort_value):
        super().__init__(display_text)
        self.setData(sort_value, Qt.ItemDataRole.UserRole)

    def __lt__(self, other):
        return self.data(Qt.ItemDataRole.UserRole) < other.data(Qt.ItemDataRole.UserRole)


class BarChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.total_size = 1
        self.setMinimumHeight(280)

    def set_data(self, tree_data):
        children = tree_data.get("children", {})
        total = tree_data["size"] or 1

        items = []
        for node in children.values():
            if node["size"] <= 0:
                continue

            # Собираем сегменты: подпапки + файлы корня папки как один сегмент
            segments = []
            files_size = 0

            for child in node.get("children", {}).values():
                if child["type"] == "directory" and child["size"] > 0:
                    segments.append({"name": child["name"], "size": child["size"]})
                elif child["type"] == "file":
                    files_size += child["size"]

            if files_size > 0:
                segments.append({"name": "[файлы]", "size": files_size})

            segments.sort(key=lambda x: -x["size"])
            items.append({"name": node["name"], "size": node["size"], "segments": segments})

        items.sort(key=lambda x: -x["size"])
        self.data = items[:10]
        self.total_size = total
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W = self.width()
        H = self.height()

        padding_top = 16
        padding_bottom = 16
        margin_left = 190
        margin_right = 140
        bar_area_w = W - margin_left - margin_right

        n = len(self.data)
        available_h = H - padding_top - padding_bottom
        row_h = available_h / n
        bar_h = max(18, min(40, row_h * 0.62))
        gap = (row_h - bar_h) / 2

        max_size = self.data[0]["size"]

        label_font = QFont()
        label_font.setPointSize(9)
        painter.setFont(label_font)

        seg_label_font = QFont()
        seg_label_font.setPointSize(8)

        for i, item in enumerate(self.data):
            y = padding_top + i * row_h + gap
            bar_w = max(2, (item["size"] / max_size) * bar_area_w)

            segments = item["segments"]

            if segments:
                # Рисуем сегменты пропорционально размеру внутри bar_w
                x_cursor = margin_left
                for j, seg in enumerate(segments):
                    seg_w = (seg["size"] / item["size"]) * bar_w
                    if seg_w < 1:
                        continue
                    color = QColor(PALETTE[j % len(PALETTE)])
                    painter.fillRect(int(x_cursor), int(y), int(seg_w), int(bar_h), color)

                    # Подпись сегмента если достаточно места
                    if seg_w > 48:
                        painter.setFont(seg_label_font)
                        painter.setPen(QColor("#ffffff"))
                        seg_label = seg["name"] if seg_w > 80 else ""
                        if seg_w > 80:
                            seg_label = seg["name"] if len(seg["name"]) * 7 < seg_w - 8 else seg["name"][:int(seg_w / 7) - 2] + "…"
                        painter.drawText(
                            QRect(int(x_cursor + 4), int(y), int(seg_w - 8), int(bar_h)),
                            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                            seg_label
                        )
                        painter.setFont(label_font)

                    x_cursor += seg_w

                # Тонкие разделители между сегментами
                x_div = margin_left
                painter.setPen(QColor(0, 0, 0, 80))
                for seg in segments[:-1]:
                    seg_w = (seg["size"] / item["size"]) * bar_w
                    x_div += seg_w
                    painter.drawLine(int(x_div), int(y), int(x_div), int(y + bar_h))
            else:
                # Нет подпапок — монотонный бар
                painter.fillRect(int(margin_left), int(y), int(bar_w), int(bar_h), QColor(PALETTE[i % len(PALETTE)]))

            # Название папки слева
            painter.setPen(QColor("#e0e0e0"))
            painter.setFont(label_font)
            name_display = item["name"] if len(item["name"]) <= 26 else item["name"][:23] + "..."
            painter.drawText(
                QRect(0, int(y), margin_left - 10, int(bar_h)),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                name_display
            )

            # Размер и процент справа
            pct = item["size"] / self.total_size * 100
            label = f"{format_size(item['size'])}  {pct:.1f}%"
            painter.setPen(QColor("#b0b0b0"))
            painter.drawText(
                QRect(int(margin_left + bar_area_w + 10), int(y), margin_right - 10, int(bar_h)),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                label
            )

        painter.end()


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

        # Горизонтальный сплиттер: слева — дерево каталогов, справа — типы файлов
        self.hsplit = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.hsplit, stretch=1)

        # Панель дерева каталогов
        tree_panel = QWidget()
        tree_layout = QVBoxLayout(tree_panel)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.addWidget(QLabel("Структура каталогов"))
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Имя", "Размер", "Тип", "Владелец", "Файлов"])
        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        tree_layout.addWidget(self.tree_view)

        # Панель типов файлов
        ext_panel = QWidget()
        ext_layout = QVBoxLayout(ext_panel)
        ext_layout.setContentsMargins(0, 0, 0, 0)
        ext_layout.addWidget(QLabel("Типы файлов (Расширения)"))
        self.ext_table = QTableWidget()
        self.ext_table.setColumnCount(3)
        self.ext_table.setHorizontalHeaderLabels(["Расширение", "Количество файлов", "Общий размер"])
        self.ext_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ext_table.setSortingEnabled(True)
        ext_layout.addWidget(self.ext_table)

        self.hsplit.addWidget(tree_panel)
        self.hsplit.addWidget(ext_panel)
        self.hsplit.setStretchFactor(0, 3)
        self.hsplit.setStretchFactor(1, 1)

        # Панель чарта с кнопкой сворачивания
        chart_header = QHBoxLayout()
        chart_header.setContentsMargins(0, 2, 0, 2)
        chart_header.addWidget(QLabel("Топ папок"))
        chart_header.addStretch()
        self.btn_toggle_chart = QPushButton("▼")
        self.btn_toggle_chart.setFixedSize(24, 24)
        self.btn_toggle_chart.clicked.connect(self.toggle_chart)
        chart_header.addWidget(self.btn_toggle_chart)
        self.layout.addLayout(chart_header)

        self.bar_chart = BarChartWidget()
        self.layout.addWidget(self.bar_chart)

    def start_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для анализа")
        if folder:
            self.current_root = folder
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

    def display_data(self, data):
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%")
        self.lbl_status.setText(f"Сканирование завершено. Общий размер: {format_size(data['size'])}")
        self.btn_scan.setEnabled(True)

        self.tree_view.setUpdatesEnabled(False)
        self.populate_tree_iterative(data)
        self.tree_view.expandToDepth(0)

        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.tree_view.setUpdatesEnabled(True)

        self.populate_extensions_tab(data)
        self.bar_chart.set_data(data)

    def populate_tree_iterative(self, root_data):
        root_item = self.model.invisibleRootItem()
        stack = [(root_item, root_data, self.current_root)]

        while stack:
            parent_item, node_data, full_path = stack.pop()

            name_item = QStandardItem(node_data["name"])
            name_item.setData(full_path, Qt.ItemDataRole.UserRole + 1)
            size_item = NumericSortItem(format_size(node_data["size"]), node_data["size"])

            node_type = node_data.get("type", "directory")

            ads_size = node_data.get("ads_size", 0)
            if node_type == "file":
                type_str = "Файл (с ADS)" if ads_size > 0 else "Файл"
            else:
                type_str = "Папка"

            type_item = QStandardItem(type_str)

            # Подсвечиваем файлы с альтернативными потоками данных
            if ads_size > 0:
                from PyQt6.QtGui import QColor
                type_item.setForeground(QColor("teal"))
                name_item.setForeground(QColor("teal"))
                # Добавляем подсказку при наведении мышкой на имя файла
                name_item.setToolTip(f"Размер скрытых потоков (ADS): {self.format_size(ads_size)}")
            # --- КОНЕЦ ВСТАВКИ ---

            owner_item = QStandardItem(node_data.get("owner", "User"))

            count_val = node_data.get("count", 0) if node_type == "directory" else 0
            count_item = NumericSortItem(str(count_val) if count_val else "", count_val)

            parent_item.appendRow([name_item, size_item, type_item, owner_item, count_item])

            if "children" in node_data and node_data["children"]:
                for child in node_data["children"].values():
                    child_path = os.path.join(full_path, child["name"])
                    stack.append((name_item, child, child_path))

    def toggle_chart(self):
        visible = self.bar_chart.isVisible()
        self.bar_chart.setVisible(not visible)
        self.btn_toggle_chart.setText("▶" if visible else "▼")

    def show_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return

        name_index = index.sibling(index.row(), 0)
        item = self.model.itemFromIndex(name_index)
        if not item:
            return

        path = item.data(Qt.ItemDataRole.UserRole + 1)
        if not path:
            return

        menu = QMenu(self)
        menu.addAction("Показать в проводнике", lambda: self.open_in_explorer(path))
        menu.addSeparator()
        menu.addAction("Удалить", lambda: self.delete_item(path))
        menu.addSeparator()
        menu.addAction("Копировать путь", lambda: self.copy_path(path))
        menu.exec(self.tree_view.viewport().mapToGlobal(pos))

    def open_in_explorer(self, path):
        if os.name == 'nt':
            subprocess.Popen(f'explorer /select,"{path}"', shell=True)
        else:
            subprocess.Popen(['xdg-open', os.path.dirname(path)])

    def delete_item(self, path):
        if os.name == 'nt':
            class SHFILEOPSTRUCT(ctypes.Structure):
                _fields_ = [
                    ('hwnd',                 ctypes.c_void_p),
                    ('wFunc',                ctypes.c_uint),
                    ('pFrom',                ctypes.c_void_p),
                    ('pTo',                  ctypes.c_void_p),
                    ('fFlags',               ctypes.c_ushort),
                    ('fAnyOperationsAborted',ctypes.c_int),
                    ('hNameMappings',        ctypes.c_void_p),
                    ('lpszProgressTitle',    ctypes.c_void_p),
                ]
            FO_DELETE   = 3
            FOF_ALLOWUNDO = 0x0040
            buf = ctypes.create_unicode_buffer(path + '\x00')
            op = SHFILEOPSTRUCT()
            op.hwnd  = int(self.winId())
            op.wFunc = FO_DELETE
            op.pFrom = ctypes.addressof(buf)
            op.fFlags = FOF_ALLOWUNDO
            ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
        else:
            subprocess.Popen(['gio', 'trash', path])

    def copy_path(self, path):
        QApplication.clipboard().setText(path)


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

            item_size_custom = TableNumItem(format_size(total_size))
            item_size_custom.setData(Qt.ItemDataRole.UserRole, total_size)

            self.ext_table.setItem(row, 0, item_ext)
            self.ext_table.setItem(row, 1, item_count)
            self.ext_table.setItem(row, 2, item_size_custom)

        self.ext_table.setSortingEnabled(True)
        self.ext_table.sortByColumn(2, Qt.SortOrder.DescendingOrder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    dark_palette = app.palette()
    dark_palette.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.WindowText,      QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.Base,            QColor(22, 22, 22))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(38, 38, 38))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase,     QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText,     QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.Text,            QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.Button,          QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.ButtonText,      QColor(220, 220, 220))
    dark_palette.setColor(QPalette.ColorRole.BrightText,      QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Link,            QColor(74, 144, 217))
    dark_palette.setColor(QPalette.ColorRole.Highlight,       QColor(74, 144, 217))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text,       QColor(100, 100, 100))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(100, 100, 100))
    app.setPalette(dark_palette)

    window = DiskUsageApp()
    window.show()
    sys.exit(app.exec())