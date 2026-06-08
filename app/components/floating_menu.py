from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
import qtawesome as qta
from qfluentwidgets import SubtitleLabel


class MiniActionCard(QFrame):
    """ Versão compacta do ActionCard para o menu flutuante """
    def __init__(self, title, fa_icon_name, is_highlight=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(230, 60)

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
        self.icon_label.setPixmap(icon.pixmap(22, 22))
        self.icon_label.setStyleSheet("background: transparent;")

        self.title_label = SubtitleLabel(title)
        self.title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #111827; background: transparent;")

        layout.addWidget(self.icon_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addStretch()


class FloatingMenu(QWidget):
    """
    Overlay fantasma em tela cheia.
    Os cards ficam ancorados nas bordas/cantos para acesso rápido por gaze:
      - Voltar Página     -> canto superior esquerdo
      - Fechar Aplicativo -> canto superior direito
      - Rolar para Cima   -> meio superior
      - Rolar para Baixo  -> meio inferior
      - Tela Cheia (Home) -> canto inferior direito
    """

    MARGIN = 30  # distância das bordas, em pixels

    def __init__(self):
        super().__init__(None)

        # Janela transparente ao input: não rouba foco nem cliques do app por trás
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.lista_cards = []

        # Cards são filhos diretos (sem layout — posicionados manualmente nas bordas)
        self.card_back_page = MiniActionCard("Voltar Página", 'fa5s.arrow-left', False, self)
        self.card_fechar_app = MiniActionCard("Fechar Aplicativo", 'fa5s.times-circle', False, self)
        self.card_scroll_up = MiniActionCard("Rolar para Cima", 'fa5s.arrow-up', False, self)
        self.card_scroll_down = MiniActionCard("Rolar para Baixo", 'fa5s.arrow-down', False, self)
        self.card_voltar = MiniActionCard("Tela Cheia (Home)", 'fa5s.expand-arrows-alt', True, self)

        self.lista_cards.extend([
            self.card_scroll_up,
            self.card_scroll_down,
            self.card_back_page,
            self.card_voltar,
            self.card_fechar_app,
        ])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposicionar_cards()

    def showEvent(self, event):
        super().showEvent(event)
        self._reposicionar_cards()

    def _reposicionar_cards(self):
        w, h = self.width(), self.height()
        m = self.MARGIN

        # Canto superior esquerdo
        self.card_back_page.move(m, m)

        # Canto superior direito
        self.card_fechar_app.move(
            w - self.card_fechar_app.width() - m,
            m,
        )

        # Meio superior (centralizado horizontalmente)
        self.card_scroll_up.move(
            (w - self.card_scroll_up.width()) // 2,
            m,
        )

        # Meio inferior (centralizado horizontalmente)
        self.card_scroll_down.move(
            (w - self.card_scroll_down.width()) // 2,
            h - self.card_scroll_down.height() - m,
        )

        # Canto inferior direito (volta para tela cheia)
        self.card_voltar.move(
            w - self.card_voltar.width() - m,
            h - self.card_voltar.height() - m,
        )
