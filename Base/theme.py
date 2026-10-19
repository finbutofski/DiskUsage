from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

# Цвета сегментов диаграммы
PALETTE = ["#4A90D9", "#5BA85A", "#E87C35", "#C94F4F", "#8B6BB1",
           "#3AADA8", "#E8C440", "#D96B8A", "#7FB3D3", "#95A5A6"]


def apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")

    p = app.palette()
    R, G = QPalette.ColorRole, QPalette.ColorGroup
    colors = {
        R.Window: (30, 30, 30),
        R.WindowText: (220, 220, 220),
        R.Base: (22, 22, 22),
        R.AlternateBase: (38, 38, 38),
        R.ToolTipBase: (220, 220, 220),
        R.ToolTipText: (220, 220, 220),
        R.Text: (220, 220, 220),
        R.Button: (45, 45, 45),
        R.ButtonText: (220, 220, 220),
        R.BrightText: (255, 255, 255),
        R.Link: (74, 144, 217),
        R.Highlight: (74, 144, 217),
        R.HighlightedText: (255, 255, 255),
    }
    for role, rgb in colors.items():
        p.setColor(role, QColor(*rgb))

    for role in (R.Text, R.ButtonText):
        p.setColor(G.Disabled, role, QColor(100, 100, 100))

    app.setPalette(p)
