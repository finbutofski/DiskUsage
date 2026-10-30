from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                             QProgressBar, QPushButton, QSplitter, QVBoxLayout, QWidget)

from filter_panel import FilterPanelWidget

from .bar_chart import ChartSection
from .extensions_panel import ExtensionsPanel
from .scan_thread import ScanThread
from .tree_panel import DirectoryTreePanel
from .utils import format_size


class DiskUsageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Space Analyzer")
        self.resize(1300, 800)

        self.current_root = ""
        self.scan_thread = None

        self._build_ui()

    # --- сборка интерфейса -------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addLayout(self._build_top_bar())

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        root.addWidget(self._build_main_splitter(), stretch=1)

        self.chart_section = ChartSection()
        root.addWidget(self.chart_section)

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        self.btn_scan = QPushButton("Выбрать папку")
        self.btn_scan.setFixedWidth(150)
        self.btn_scan.clicked.connect(self.start_scan)

        self.lbl_status = QLabel("Готов к работе")
        bar.addWidget(self.btn_scan)
        bar.addWidget(self.lbl_status)
        return bar

    def _build_main_splitter(self) -> QSplitter:
        self.tree_panel = DirectoryTreePanel()

        self.ext_panel = ExtensionsPanel()
        self.filter_panel = FilterPanelWidget()
        self.filter_panel.filter_changed.connect(
            lambda: self.tree_panel.apply_filters(self.filter_panel)
        )

        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(self.ext_panel, stretch=1)
        sidebar_layout.addWidget(self.filter_panel)

        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.tree_panel)
        split.addWidget(sidebar)
        split.setStretchFactor(0, 7)
        split.setStretchFactor(1, 3)
        split.setSizes([900, 400])
        return split

    # --- сканирование ------------------------------------------------------

    def start_scan(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для анализа")
        if not folder:
            return

        self.current_root = folder
        self.tree_panel.clear()
        self.ext_panel.clear()

        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Подготовка к сканированию (подсчет файлов)...")
        self.btn_scan.setEnabled(False)
        self.tree_panel.set_sorting_enabled(False)

        self.scan_thread = ScanThread(folder)
        self.scan_thread.count_finished.connect(self.setup_progress_bar)
        self.scan_thread.progress.connect(self.update_progress)
        self.scan_thread.scan_finished.connect(self.display_data)
        self.scan_thread.start()

    def setup_progress_bar(self, total_items: int):
        self.progress_bar.setMaximum(total_items)
        self.progress_bar.setFormat("%p% (%v / %m)")

    def update_progress(self, path: str, current_count: int):
        # Если во время сканирования появились новые файлы — расширяем максимум
        if current_count > self.progress_bar.maximum():
            self.progress_bar.setMaximum(current_count + 100)
        self.progress_bar.setValue(current_count)

        if len(path) > 60:
            path = "..." + path[-57:]
        self.lbl_status.setText(f"Сканирую: {path}")

    def display_data(self, data: dict):
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("100%")
        self.lbl_status.setText(
            f"Сканирование завершено. Общий размер: {format_size(data['size'])}"
        )
        self.btn_scan.setEnabled(True)

        self.tree_panel.load(data, self.current_root)
        self.ext_panel.load(data)
        self.chart_section.set_data(data)
