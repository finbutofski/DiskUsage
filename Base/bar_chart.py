from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .theme import PALETTE
from .utils import format_size

TOP_N = 10
MARGIN_LEFT = 190
MARGIN_RIGHT = 140
PADDING_V = 16
AlignL = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
AlignR = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


def build_chart_data(tree_data: dict, top_n: int = TOP_N) -> list:
    """Топ-N папок первого уровня; каждая разбита на сегменты (подпапки + [файлы])."""
    items = []
    for node in tree_data.get("children", {}).values():
        if node["size"] <= 0:
            continue

        segments = []
        files_size = 0
        for child in node.get("children", {}).values():
            if child["type"] == "directory" and child["size"] > 0:
                segments.append({"name": child["name"], "size": child["size"]})
            elif child["type"] == "file":
                files_size += child["size"]

        if files_size > 0:
            segments.append({"name": "[файлы]", "size": files_size})

        segments.sort(key=lambda s: -s["size"])
        items.append({"name": node["name"], "size": node["size"], "segments": segments})

    items.sort(key=lambda i: -i["size"])
    return items[:top_n]


class BarChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []
        self.total_size = 1
        self.setMinimumHeight(200)

    def set_data(self, tree_data: dict) -> None:
        self.data = build_chart_data(tree_data)
        self.total_size = tree_data["size"] or 1
        self.update()

    # --- отрисовка ---------------------------------------------------------

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._label_font = QFont()
        self._label_font.setPointSize(9)
        self._seg_font = QFont()
        self._seg_font.setPointSize(8)
        painter.setFont(self._label_font)

        bar_area_w = self.width() - MARGIN_LEFT - MARGIN_RIGHT
        row_h = (self.height() - 2 * PADDING_V) / len(self.data)
        bar_h = max(18, min(40, row_h * 0.62))
        gap = (row_h - bar_h) / 2
        max_size = self.data[0]["size"]

        for i, item in enumerate(self.data):
            y = PADDING_V + i * row_h + gap
            bar_w = max(2, item["size"] / max_size * bar_area_w)

            self._draw_bar(painter, item, i, y, bar_h, bar_w)
            self._draw_name(painter, item["name"], y, bar_h)
            self._draw_value(painter, item, y, bar_h, bar_area_w)

        painter.end()

    def _draw_bar(self, p, item, index, y, bar_h, bar_w):
        segments = item["segments"]
        if not segments:
            p.fillRect(MARGIN_LEFT, int(y), int(bar_w), int(bar_h),
                       QColor(PALETTE[index % len(PALETTE)]))
            return

        x = MARGIN_LEFT
        for j, seg in enumerate(segments):
            seg_w = seg["size"] / item["size"] * bar_w
            if seg_w < 1:
                continue
            p.fillRect(int(x), int(y), int(seg_w), int(bar_h), QColor(PALETTE[j % len(PALETTE)]))
            self._draw_segment_label(p, seg["name"], x, y, seg_w, bar_h)
            x += seg_w

        # тонкие разделители
        p.setPen(QColor(0, 0, 0, 80))
        x = MARGIN_LEFT
        for seg in segments[:-1]:
            x += seg["size"] / item["size"] * bar_w
            p.drawLine(int(x), int(y), int(x), int(y + bar_h))

    def _draw_segment_label(self, p, name, x, y, seg_w, bar_h):
        if seg_w <= 80:
            return
        max_chars = int(seg_w / 7)
        label = name if len(name) * 7 < seg_w - 8 else name[:max_chars - 2] + "…"

        p.setFont(self._seg_font)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(int(x + 4), int(y), int(seg_w - 8), int(bar_h)), AlignL, label)
        p.setFont(self._label_font)

    def _draw_name(self, p, name, y, bar_h):
        text = name if len(name) <= 26 else name[:23] + "..."
        p.setPen(QColor("#e0e0e0"))
        p.drawText(QRect(0, int(y), MARGIN_LEFT - 10, int(bar_h)), AlignR, text)

    def _draw_value(self, p, item, y, bar_h, bar_area_w):
        pct = item["size"] / self.total_size * 100
        text = f"{format_size(item['size'])}  {pct:.1f}%"
        p.setPen(QColor("#b0b0b0"))
        p.drawText(
            QRect(int(MARGIN_LEFT + bar_area_w + 10), int(y), MARGIN_RIGHT - 10, int(bar_h)),
            AlignL, text,
        )


class ChartSection(QWidget):
    """Заголовок «Топ папок» со сворачиваемой диаграммой."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.chart = BarChartWidget()

        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedSize(24, 24)
        self.btn_toggle.clicked.connect(self.toggle)

        header = QHBoxLayout()
        header.setContentsMargins(0, 2, 0, 2)
        header.addWidget(QLabel("Топ папок"))
        header.addStretch()
        header.addWidget(self.btn_toggle)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.chart)

    def set_data(self, tree_data: dict) -> None:
        self.chart.set_data(tree_data)

    def toggle(self) -> None:
        visible = self.chart.isVisible()
        self.chart.setVisible(not visible)
        self.btn_toggle.setText("▶" if visible else "▼")
