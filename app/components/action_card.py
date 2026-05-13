from PySide6.QtWidgets import QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
import qtawesome as qta
from qfluentwidgets import ElevatedCardWidget, SubtitleLabel, BodyLabel

class ActionCard(ElevatedCardWidget):
    def __init__(self, title, description, fa_icon_name, is_highlight=False, parent=None):
        super().__init__(parent)
        # Mantemos o tamanho grande para a Lei de Fitts (Eye Tracking)
        self.setFixedSize(400, 260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # --- CAIXA DO ÍCONE ---
        self.icon_box = QFrame(self)
        self.icon_box.setFixedSize(70, 70)
        
        # Cores iguais à sua imagem de referência
        bg_color = '#E0E7FF' if is_highlight else '#F3F4F6'
        icon_color = '#4F46E5' if is_highlight else '#111827'
        self.icon_box.setStyleSheet(f"background-color: {bg_color}; border-radius: 16px;")
        
        box_layout = QVBoxLayout(self.icon_box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        
        # Injetando o ícone do QtAwesome (vetorial e perfeito)
        self.icon_label = QLabel()
        icon = qta.icon(fa_icon_name, color=icon_color)
        self.icon_label.setPixmap(icon.pixmap(32, 32))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box_layout.addWidget(self.icon_label)

        # --- TEXTOS (Usando a tipografia nativa do Fluent) ---
        self.title_label = SubtitleLabel(title)
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        
        self.desc_label = BodyLabel(description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #6B7280; font-size: 14px;")

        # Montagem do Layout
        layout.addWidget(self.icon_box)
        layout.addSpacing(40)
        layout.addWidget(self.title_label)
        layout.addSpacing(10)
        layout.addWidget(self.desc_label)