from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt
import qtawesome as qta
from qfluentwidgets import TitleLabel, BodyLabel, SubtitleLabel


# ---------------------------------------------------------------------------
# CONTEÚDO DO TUTORIAL
# Cada "passo" possui uma lista de páginas. Cada página tem um título e uma
# lista de dicas (ícone FontAwesome + texto).
# ---------------------------------------------------------------------------
TUTORIAIS = {
    "home": [
        {
            "titulo": "Esta é a sua Tela Inicial",
            "dicas": [
                ('fa5s.eye', "Controle tudo com o olhar: mantenha o foco sobre um cartão para selecioná-lo."),
                ('fa5s.circle', "O círculo verde mostra o progresso. Quando ele se completar, o cartão é ativado."),
                ('fa5s.th-large', "Use os cartões para calibrar, abrir aplicativos ou ajustar as configurações."),
            ],
        },
        {
            "titulo": "Dica de uso",
            "dicas": [
                ('fa5s.user-lock', "Mantenha a cabeça parada e mova apenas os olhos para maior precisão."),
                ('fa5s.redo', "Se o cursor sair do lugar, refaça a calibração pelo cartão 'Começar Calibração'."),
            ],
        },
    ],
    "apps": [
        {
            "titulo": "Aplicativos",
            "dicas": [
                ('fa5s.th-large', "Aqui você abre programas do computador apenas olhando para eles."),
                ('fa5s.desktop', "Ao abrir um app, o EyeControl entra no Modo Windows e mostra um menu flutuante."),
            ],
        },
    ],
    "settings": [
        {
            "titulo": "Configurações",
            "dicas": [
                ('fa5s.sliders-h', "Ajuste a sensibilidade e o tempo de foco (dwell) conforme o seu conforto."),
                ('fa5s.bullseye', "Use o botão de recalibrar sempre que sentir o cursor impreciso."),
            ],
        },
    ],
    "windows": [
        {
            "titulo": "Modo Windows",
            "dicas": [
                ('fa5s.border-all', "Agora você controla o computador. Os comandos ficam nas bordas da tela."),
                ('fa5s.arrows-alt-v', "Olhe para os cartões de cima/baixo para rolar a página."),
                ('fa5s.mouse-pointer', "Use o cartão 'Clicar' para dar um clique em qualquer lugar."),
                ('fa5s.expand-arrows-alt', "O cartão 'Tela Cheia (Home)' devolve você ao EyeControl."),
            ],
        },
    ],
    "click": [
        {
            "titulo": "Como clicar com o olhar",
            "dicas": [
                ('fa5s.crosshairs', "1. Olhe para o local onde deseja clicar. Você tem alguns segundos para mirar."),
                ('fa5s.times', "2. Um 'X' vermelho vai travar no ponto escolhido."),
                ('fa5s.check-circle', "3. Mantenha o olhar sobre o 'X' para confirmar e disparar o clique."),
                ('fa5s.redo', "Para mudar o local, olhe novamente para o cartão 'Clicar'."),
            ],
        },
    ],
}


class _DicaLinha(QFrame):
    """Uma linha de dica: ícone + texto."""

    def __init__(self, fa_icon, texto, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(16)

        icon_label = QLabel()
        icon = qta.icon(fa_icon, color='#4F46E5')
        icon_label.setPixmap(icon.pixmap(28, 28))
        icon_label.setStyleSheet("background: transparent; border: none;")
        icon_label.setFixedWidth(34)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        texto_label = BodyLabel(texto)
        texto_label.setStyleSheet("color: #374151; font-size: 16px; background: transparent; border: none;")
        texto_label.setWordWrap(True)

        layout.addWidget(icon_label)
        layout.addWidget(texto_label, 1)


class _BotaoTutorial(QFrame):
    """Botão dwellável (selecionável pelo olhar) para avançar o tutorial."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(280, 64)
        self.setStyleSheet(
            "QFrame { background-color: #4F46E5; border-radius: 14px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 5, 20, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel()
        icon = qta.icon('fa5s.check', color='#FFFFFF')
        self.icon_label.setPixmap(icon.pixmap(22, 22))
        self.icon_label.setStyleSheet("background: transparent; border: none;")

        # title_label é lido pelo sistema de dwell do main.py
        self.title_label = SubtitleLabel("Entendi")
        self.title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #FFFFFF; background: transparent; border: none;"
        )

        layout.addWidget(self.icon_label)
        layout.addSpacing(10)
        layout.addWidget(self.title_label)


class TutorialOverlay(QWidget):
    """
    Overlay de tutorial em tela cheia, controlado pelo olhar.

    Escurece a tela, mostra um painel com as dicas do passo atual e um botão
    'Entendi' (dwellável). O main.py controla o foco no botão e chama
    proximo() quando o dwell se completa.
    """

    def __init__(self):
        super().__init__(None)
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

        self._paginas = []
        self._indice = 0

        # --- Layout central ---
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.painel = QFrame()
        self.painel.setFixedWidth(760)
        self.painel.setObjectName("TutorialPanel")
        self.painel.setStyleSheet(
            "#TutorialPanel { background-color: #FFFFFF; border-radius: 24px; border: 1px solid #E5E7EB; }"
        )
        painel_layout = QVBoxLayout(self.painel)
        painel_layout.setContentsMargins(45, 40, 45, 40)
        painel_layout.setSpacing(10)

        self.label_passo = BodyLabel("")
        self.label_passo.setStyleSheet(
            "color: #4F46E5; font-size: 14px; font-weight: bold; background: transparent; border: none;"
        )
        self.label_passo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.titulo = TitleLabel("")
        self.titulo.setStyleSheet(
            "font-size: 28px; font-weight: 800; color: #111827; background: transparent; border: none;"
        )
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titulo.setWordWrap(True)

        # Container das dicas (recriado a cada página)
        self.dicas_container = QWidget()
        self.dicas_container.setStyleSheet("background: transparent;")
        self.dicas_layout = QVBoxLayout(self.dicas_container)
        self.dicas_layout.setContentsMargins(0, 0, 0, 0)
        self.dicas_layout.setSpacing(4)

        # Botão dwellável
        botao_box = QHBoxLayout()
        botao_box.addStretch()
        self.btn_card = _BotaoTutorial()
        botao_box.addWidget(self.btn_card)
        botao_box.addStretch()

        painel_layout.addWidget(self.label_passo)
        painel_layout.addSpacing(4)
        painel_layout.addWidget(self.titulo)
        painel_layout.addSpacing(20)
        painel_layout.addWidget(self.dicas_container)
        painel_layout.addSpacing(28)
        painel_layout.addLayout(botao_box)

        outer.addWidget(self.painel)

    # ------------------------------------------------------------------ API
    def mostrar_passo(self, step_key):
        """Carrega as páginas do passo e mostra o overlay na primeira página."""
        self._paginas = TUTORIAIS.get(step_key, [])
        self._indice = 0
        if not self._paginas:
            return
        self._renderizar_pagina()
        self.show()
        self.raise_()

    def proximo(self):
        """
        Avança para a próxima página.
        Retorna True se ainda há páginas; False se o tutorial terminou.
        """
        self._indice += 1
        if self._indice >= len(self._paginas):
            return False
        self._renderizar_pagina()
        return True

    # ------------------------------------------------------------- internos
    def _renderizar_pagina(self):
        pagina = self._paginas[self._indice]
        total = len(self._paginas)

        if total > 1:
            self.label_passo.setText(f"PASSO {self._indice + 1} DE {total}")
            self.label_passo.show()
        else:
            self.label_passo.hide()

        self.titulo.setText(pagina["titulo"])

        # Limpa dicas anteriores
        while self.dicas_layout.count():
            item = self.dicas_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        for fa_icon, texto in pagina["dicas"]:
            self.dicas_layout.addWidget(_DicaLinha(fa_icon, texto))

        # Texto do botão: 'Avançar' enquanto houver páginas, 'Entendi' na última
        if self._indice < total - 1:
            self.btn_card.title_label.setText("Avançar")
        else:
            self.btn_card.title_label.setText("Entendi")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(17, 24, 39, 180))
