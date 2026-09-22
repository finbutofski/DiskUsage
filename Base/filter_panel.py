from PyQt6.QtWidgets import (QGroupBox, QFormLayout, QLineEdit,
                             QSpinBox, QComboBox)
from PyQt6.QtCore import pyqtSignal


class FilterPanelWidget(QGroupBox):
    """
    Виджет графической панели управления фильтрами.
    При изменении любого поля излучает сигнал `filter_changed`.
    """
    filter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Фильтрация файлов и папок", parent)

        layout = QFormLayout(self)

        # 1. Поле ввода расширений
        self.txt_ext = QLineEdit()
        self.txt_ext.setPlaceholderText("например: png, jpg, pdf")
        self.txt_ext.textChanged.connect(self.filter_changed.emit)

        # 2. Выпадающий список периода времени
        self.combo_time = QComboBox()
        self.combo_time.addItems([
            "За все время",
            "За последние 24 часа",
            "За последние 7 дней",
            "За 30 дней",
            "За 365 дней"
        ])
        self.combo_time.currentIndexChanged.connect(self.filter_changed.emit)

        # 3. Диапазон размера (в МБ)
        self.spin_min_mb = QSpinBox()
        self.spin_min_mb.setRange(0, 10_000_000)
        self.spin_min_mb.setSuffix(" МБ")
        self.spin_min_mb.valueChanged.connect(self.filter_changed.emit)

        self.spin_max_mb = QSpinBox()
        self.spin_max_mb.setRange(0, 10_000_000)
        self.spin_max_mb.setValue(10_000_000)
        self.spin_max_mb.setSuffix(" МБ")
        self.spin_max_mb.valueChanged.connect(self.filter_changed.emit)

        # 4. Поле ввода владельца
        self.txt_owner = QLineEdit()
        self.txt_owner.setPlaceholderText("Имя пользователя")
        self.txt_owner.textChanged.connect(self.filter_changed.emit)

        # 5. Глубина вложенности
        self.spin_depth = QSpinBox()
        self.spin_depth.setRange(0, 50)
        self.spin_depth.setSpecialValueText("Без ограничений")
        self.spin_depth.valueChanged.connect(self.filter_changed.emit)

        # Добавляем все элементы на форму
        layout.addRow("Расширения:", self.txt_ext)
        layout.addRow("Время изменения:", self.combo_time)
        layout.addRow("Мин. размер:", self.spin_min_mb)
        layout.addRow("Макс. размер:", self.spin_max_mb)
        layout.addRow("Владелец:", self.txt_owner)
        layout.addRow("Глубина вложенности:", self.spin_depth)