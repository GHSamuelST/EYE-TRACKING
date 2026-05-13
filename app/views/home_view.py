from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from PySide6.QtCore import Qt
from qfluentwidgets import TitleLabel, BodyLabel
from components.action_card import ActionCard

class HomeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HomeView")

        # --- 1. O LAYOUT GRAVITACIONAL ---
        # Este layout principal vai forçar o container interno a ficar no centro
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        # O container que agrupa textos e cards
        content_container = QWidget()
        layout = QVBoxLayout(content_container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- CABEÇALHO ---
        self.title = TitleLabel("Bem-vindo ao EyeControl")
        self.title.setStyleSheet("font-size: 38px; color: #111827; font-weight: 800;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter) # Texto centralizado
        
        self.subtitle = BodyLabel("Mantenha o foco sobre uma opção para selecioná-la. A interface responderá ao seu olhar.")
        self.subtitle.setStyleSheet("font-size: 16px; color: #4B5563;")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter) # Texto centralizado

        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(10)
        layout.addWidget(self.subtitle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(60)

        # --- GRID DE AÇÕES ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(30)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) # Grid centralizada

        card1 = ActionCard("Começar Calibração", "Ajuste a precisão do rastreamento ocular para sua posição atual.", 'fa5s.expand', True)
        card2 = ActionCard("Falar (Voz)", "Acesse o teclado preditivo e frases rápidas para comunicação.", 'fa5s.headset', False)
        card3 = ActionCard("Abrir Aplicativos", "Navegue pela web, entretenimento e ferramentas de automação.", 'fa5s.th-large', False)
        card4 = ActionCard("Configurações", "Personalize a sensibilidade, tempo de permanência e aparência.", 'fa5s.sliders-h', False)

        grid_layout.addWidget(card1, 0, 0)
        grid_layout.addWidget(card2, 0, 1)
        grid_layout.addWidget(card3, 1, 0)
        grid_layout.addWidget(card4, 1, 1)

        layout.addLayout(grid_layout)
        
        # Adiciona o container (já montado) no meio exato da tela
        main_layout.addWidget(content_container, alignment=Qt.AlignmentFlag.AlignCenter)