from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
import qtawesome as qta
from qfluentwidgets import SubtitleLabel

class MiniActionCard(QFrame):
    """ Versão compacta do ActionCard para o menu flutuante """
    def __init__(self, title, fa_icon_name, is_highlight=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(250, 65) # Um pouco mais fino para caberem mais opções
        
        bg_color = "#E0E7FF" if is_highlight else "#F3F4F6"
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border-radius: 12px; border: 1px solid transparent; }}"
            f"QFrame:hover {{ background-color: #E5E7EB; border: 1px solid #D1D5DB; }}"
        )
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        self.icon_label = QLabel()
        icon_color = '#4F46E5' if is_highlight else '#111827'
        icon = qta.icon(fa_icon_name, color=icon_color)
        self.icon_label.setPixmap(icon.pixmap(24, 24))
        self.icon_label.setStyleSheet("background: transparent;")
        
        self.title_label = SubtitleLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #111827; background: transparent;")
        
        layout.addWidget(self.icon_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addStretch()


class FloatingMenu(QWidget):
    """ Barra de Ferramentas Fantasma do Windows """
    def __init__(self):
        super().__init__(None) 
        
        # --- NOVO: Flags para não roubar o foco do Navegador! ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus  # <--- MAGIA 1
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating) # <--- MAGIA 2
        
        self.setFixedWidth(290)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(0, 0, 15, 0)
        layout.setSpacing(10) # Espaço menor entre os botões
        
        self.lista_cards = []
        
        # --- O CONTROLE REMOTO DO WINDOWS ---
        self.card_scroll_up = MiniActionCard("Rolar para Cima", 'fa5s.arrow-up', False)
        self.card_scroll_down = MiniActionCard("Rolar para Baixo", 'fa5s.arrow-down', False)
        self.card_back_page = MiniActionCard("Voltar Página", 'fa5s.arrow-left', False)
        self.card_voltar = MiniActionCard("Tela Cheia (Home)", 'fa5s.expand-arrows-alt', True)
        self.card_fechar_app = MiniActionCard("Fechar Aplicativo", 'fa5s.times-circle', False)
        
        self.lista_cards.extend([
            self.card_scroll_up, 
            self.card_scroll_down, 
            self.card_back_page, 
            self.card_voltar, 
            self.card_fechar_app
        ])
        
        for card in self.lista_cards:
            layout.addWidget(card)