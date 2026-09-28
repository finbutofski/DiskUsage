from PyQt6.QtWidgets import (QGroupBox, QFormLayout, QLineEdit,
                             QSpinBox, QComboBox, QPushButton, QHBoxLayout, QLabel)
from PyQt6.QtCore import pyqtSignal


class FilterPanelWidget(QGroupBox):
    filter_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Фильтрация файлов", parent)

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setVerticalSpacing(6)

        # 1. Расширения
        self.txt_ext = QLineEdit()
        self.txt_ext.setPlaceholderText("csproj, png, txt")

        # 2. Время изменения
        self.combo_time = QComboBox()
        self.combo_time.addItems([
            "За все время",
            "За последние 24 часа",
            "За последние 7 дней",
            "За 30 дней",
            "За 365 дней"
        ])

        # 3. Мин / Макс размер в одну строку для экономии места
        size_layout = QHBoxLayout()
        self.spin_min_mb = QSpinBox()
        self.spin_min_mb.setRange(0, 10_000_000)
        self.spin_min_mb.setSuffix(" МБ")

        self.spin_max_mb = QSpinBox()
        self.spin_max_mb.setRange(0, 10_000_000)
        self.spin_max_mb.setValue(10_000_000)
        self.spin_max_mb.setSuffix(" МБ")

        size_layout.addWidget(self.spin_min_mb)
        size_layout.addWidget(QLabel("—"))
        size_layout.addWidget(self.spin_max_mb)

        # 4. Владелец
        self.txt_owner = QLineEdit()
        self.txt_owner.setPlaceholderText("Имя пользователя")

        # 5. Глубина
        self.spin_depth = QSpinBox()
        self.spin_depth.setRange(0, 50)
        self.spin_depth.setSpecialValueText("Без ограничений")

        # 6. Кнопки
        btn_layout = QHBoxLayout()
        self.btn_apply = QPushButton("Применить")
        self.btn_apply.setStyleSheet("font-weight: bold;")
        self.btn_apply.clicked.connect(self.filter_changed.emit)

        self.btn_reset = QPushButton("Сбросить")
        self.btn_reset.clicked.connect(self.reset_filters)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_reset)

        # Добавляем все элементы
        layout.addRow("Расширения:", self.txt_ext)
        layout.addRow("Время:", self.combo_time)
        layout.addRow("Размер (от/до):", size_layout)
        layout.addRow("Владелец:", self.txt_owner)
        layout.addRow("Глубина:", self.spin_depth)
        layout.addRow(btn_layout)

    def reset_filters(self):
        """Сброс полей к исходным значениям."""
        self.txt_ext.clear()
        self.combo_time.setCurrentIndex(0)
        self.spin_min_mb.setValue(0)
        self.spin_max_mb.setValue(10_000_000)
        self.txt_owner.clear()
        self.spin_depth.setValue(0)
        self.filter_changed.emit()