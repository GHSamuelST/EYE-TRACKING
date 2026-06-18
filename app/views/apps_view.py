from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout
from PySide6.QtCore import Qt
from qfluentwidgets import TitleLabel, BodyLabel
from components.action_card import ActionCard
from components.nav_card import BackCard

class AppsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppsView")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        content_container = QWidget()
        layout = QVBoxLayout(content_container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.title = TitleLabel("Aplicativos")
        self.title.setStyleSheet("font-size: 38px; color: #111827; font-weight: 800;")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        layout.addSpacing(60)

        # --- GRID DE APPS ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(30)
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lista_cards = []
        
        card_browser = ActionCard("Navegador Web", "Abrir o Microsoft Edge", 'fa5b.edge', True)
        card_explorer = ActionCard("Arquivos", "Abrir o Explorador", 'fa5s.folder-open', False)

        self.lista_cards.extend([card_browser, card_explorer])

        for i, card in enumerate(self.lista_cards):
            grid_layout.addWidget(card, i // 2, i % 2)

        layout.addLayout(grid_layout)

        # --- BOTÃO VOLTAR (selecionável pelo olhar) ---
        layout.addSpacing(40)
        self.card_voltar = BackCard("Voltar para Home")
        self.lista_cards.append(self.card_voltar)
        layout.addWidget(self.card_voltar, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(content_container, alignment=Qt.AlignmentFlag.AlignCenter)