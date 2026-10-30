from PyQt6.QtCore import QThread, pyqtSignal

from tree_builder import count_items, get_tree


class ScanThread(QThread):
    """Сканирование папки в фоне с отчётом о прогрессе."""

    count_finished = pyqtSignal(int)   # общее число элементов
    progress = pyqtSignal(str, int)    # текущий путь, сколько обработано
    # Не называем «finished», чтобы не перекрывать QThread.finished
    scan_finished = pyqtSignal(dict)   # итоговое дерево

    def __init__(self, root_path: str):
        super().__init__()
        self.root_path = root_path

    def run(self):
        self.count_finished.emit(count_items(self.root_path))
        tree = get_tree(
            self.root_path,
            progress_callback=lambda path, count: self.progress.emit(path, count),
        )
        self.scan_finished.emit(tree)
