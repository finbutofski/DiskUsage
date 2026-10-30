from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHeaderView, QLabel, QMenu, QTreeView, QVBoxLayout, QWidget

from filter_model import DiskFilterProxyModel

from . import file_actions
from .tree_model import PATH_ROLE, create_model, populate_model

DAYS_BY_INDEX = {0: None, 1: 1, 2: 7, 3: 30, 4: 365}
MB = 1024 * 1024
MAX_SIZE_SPIN = 10_000_000  # значение «без ограничения» в спинбоксе


class DirectoryTreePanel(QWidget):
    """Дерево каталогов + прокси-фильтр + контекстное меню."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.model = create_model()
        self.proxy_model = DiskFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.model)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.proxy_model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Структура каталогов"))
        layout.addWidget(self.tree_view)

    # --- загрузка данных ---------------------------------------------------

    def clear(self) -> None:
        self.model.removeRows(0, self.model.rowCount())

    def set_sorting_enabled(self, enabled: bool) -> None:
        self.tree_view.setSortingEnabled(enabled)

    def load(self, data: dict, root_path: str) -> None:
        self.tree_view.setUpdatesEnabled(False)
        populate_model(self.model, data, root_path)
        self.tree_view.expandToDepth(0)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(1, Qt.SortOrder.DescendingOrder)
        self.tree_view.setUpdatesEnabled(True)

    # --- фильтры -----------------------------------------------------------

    def apply_filters(self, panel) -> None:
        """Переносит значения с FilterPanelWidget в прокси-модель."""
        pm = self.proxy_model
        pm.ext_filter = panel.txt_ext.text()

        pm.size_min = panel.spin_min_mb.value() * MB
        max_mb = panel.spin_max_mb.value()
        pm.size_max = max_mb * MB if max_mb < MAX_SIZE_SPIN else float("inf")

        pm.time_days = DAYS_BY_INDEX.get(panel.combo_time.currentIndex())
        pm.owner_filter = panel.txt_owner.text()

        depth = panel.spin_depth.value()
        pm.max_depth = depth if depth > 0 else None

        pm.invalidateFilter()
        self.tree_view.expandAll()

    # --- контекстное меню --------------------------------------------------

    def _path_at(self, pos):
        proxy_index = self.tree_view.indexAt(pos)
        if not proxy_index.isValid():
            return None
        source_index = self.proxy_model.mapToSource(proxy_index)
        name_index = source_index.sibling(source_index.row(), 0)
        item = self.model.itemFromIndex(name_index)
        return item.data(PATH_ROLE) if item else None

    def _show_context_menu(self, pos):
        path = self._path_at(pos)
        if not path:
            return

        menu = QMenu(self)
        menu.addAction("Показать в проводнике", lambda: file_actions.open_in_explorer(path))
        menu.addSeparator()
        menu.addAction("Удалить", lambda: file_actions.move_to_trash(path, int(self.winId())))
        menu.addSeparator()
        menu.addAction("Копировать путь", lambda: file_actions.copy_path(path))
        menu.exec(self.tree_view.viewport().mapToGlobal(pos))
