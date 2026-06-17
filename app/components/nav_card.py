from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
import qtawesome as qta
from qfluentwidgets import SubtitleLabel


class BackCard(QFrame):
    """
    Card compacto de navegação (selecionável pelo olhar).
    Expõe `title_label` para que o roteador de dwell do main.py leia o texto.
    """

    def __init__(self, title="Voltar para Home", fa_icon='fa5s.arrow-left', parent=None):
        super().__init__(parent)
        self.setObjectName("BackCard")
        self.setFixedSize(280, 70)
        self.setStyleSheet(
            "#BackCard { background-color: #F3F4F6; border-radius: 14px; border: 1px solid transparent; }"
            "#BackCard:hover { background-color: #E5E7EB; border: 1px solid #D1D5DB; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        icon = qta.icon(fa_icon, color='#111827')
        self.icon_label.setPixmap(icon.pixmap(22, 22))
        self.icon_label.setStyleSheet("background: transparent; border: none;")

        self.title_label = SubtitleLabel(title)
        self.title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #111827; background: transparent; border: none;"
        )

        layout.addWidget(self.icon_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addStretch()
