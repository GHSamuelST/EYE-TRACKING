from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
)
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import TitleLabel, SubtitleLabel, BodyLabel, PushButton
import qtawesome as qta


class _StepCard(QFrame):
    """Cartão de uma instrução com ícone, título e descrição."""

    def __init__(self, fa_icon, title, description, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #F3F4F6; border-radius: 16px; }"
        )
        self.setFixedHeight(120)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(20)

        icon_label = QLabel()
        icon = qta.icon(fa_icon, color='#4F46E5')
        icon_label.setPixmap(icon.pixmap(40, 40))
        icon_label.setStyleSheet("background: transparent;")
        icon_label.setFixedWidth(50)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        text_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        titulo = SubtitleLabel(title)
        titulo.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #111827; background: transparent;"
        )
        desc = BodyLabel(description)
        desc.setStyleSheet("color: #4B5563; font-size: 14px; background: transparent;")
        desc.setWordWrap(True)

        text_box.addWidget(titulo)
        text_box.addWidget(desc)

        layout.addWidget(icon_label)
        layout.addLayout(text_box, 1)


class OnboardingView(QWidget):
    """
    Tela de boas-vindas exibida apenas na primeira execução.
    Lista os passos para uma calibração bem-sucedida.
    """

    iniciar_clicado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OnboardingView")
        self.setStyleSheet("background-color: #F8F9FA;")

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(50, 40, 50, 40)

        container = QWidget()
        container.setFixedWidth(720)
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        # ---- Cabeçalho ----
        title = TitleLabel("Bem-vindo ao EyeControl OS")
        title.setStyleSheet("font-size: 32px; font-weight: 800; color: #111827;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = BodyLabel(
            "Antes de começar, prepare o ambiente para uma calibração precisa."
        )
        subtitle.setStyleSheet("color: #4B5563; font-size: 15px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # ---- Passos ----
        layout.addWidget(_StepCard(
            'fa5s.ruler-horizontal',
            "Distância de ~50 cm",
            "Sente-se com o rosto a aproximadamente meio braço da tela."
        ))
        layout.addWidget(_StepCard(
            'fa5s.lightbulb',
            "Boa iluminação no rosto",
            "Evite contraluz (janelas atrás de você). Luz frontal estável funciona melhor."
        ))
        layout.addWidget(_StepCard(
            'fa5s.user-lock',
            "Mantenha a cabeça parada",
            "Durante a calibração, mova apenas os olhos — a cabeça deve ficar imóvel."
        ))
        layout.addWidget(_StepCard(
            'fa5s.bullseye',
            "Olhe para os 5 pontos",
            "Um por vez, mantenha o foco até o círculo verde se completar."
        ))

        layout.addSpacing(20)

        # ---- Botão de início ----
        botao_box = QHBoxLayout()
        botao_box.addStretch()
        self.btn_iniciar = PushButton(
            qta.icon('fa5s.play', color='#FFFFFF'),
            "Iniciar Calibração"
        )
        self.btn_iniciar.setStyleSheet(
            "QPushButton { background-color: #4F46E5; color: white; border-radius: 12px; "
            "padding: 14px 30px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        self.btn_iniciar.setFixedHeight(56)
        self.btn_iniciar.clicked.connect(self.iniciar_clicado.emit)
        botao_box.addWidget(self.btn_iniciar)
        botao_box.addStretch()
        layout.addLayout(botao_box)

        outer.addWidget(container)
