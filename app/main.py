import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

class TransparentTestApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- CONFIGURAÇÃO DO WIDGET CENTRAL ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Um layout vertical padrão
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # --- CRIANDO O BOTÃO ---
        self.btn_toggle = QPushButton("Sair da Tela Cheia")
        self.btn_toggle.setFixedSize(250, 60)
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #ff4757;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border-radius: 30px;
                border: 2px solid #ffffff;
            }
            QPushButton:hover { background-color: #ff6b81; }
        """)
        
        # Conecta o clique à nossa função de alternância
        self.btn_toggle.clicked.connect(self.alternar_modo_janela)

        # Adiciona o botão ao layout e o centraliza perfeitamente
        layout.addWidget(self.btn_toggle, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- ESTADO INICIAL: TELA CHEIA E TRANSPARENTE ---
        self.tela_cheia = True
        self.ativar_tela_cheia_transparente()

    def ativar_tela_cheia_transparente(self):
        # 1. Remove a barra superior e botões de minimizar/fechar
        # Adicionamos o WindowStaysOnTopHint para garantir que fique por cima de tudo
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # 2. Torna o fundo do aplicativo translúcido/transparente
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # 3. Força a janela a ocupar a tela inteira (F11)
        self.showFullScreen()

    def alternar_modo_janela(self):
        if self.tela_cheia:
            # --- SAIR DO F11 E VOLTAR AO NORMAL ---
            self.tela_cheia = False
            self.btn_toggle.setText("Voltar para Tela Cheia")
            
            # Devolve a barra superior padrão do sistema operacional
            self.setWindowFlags(Qt.WindowType.Window)
            
            # Desativa a transparência (se não desativar, o fundo fica preto na janela normal)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            
            # Define um tamanho normal de janela
            self.resize(800, 600)
            
            # Mostra a janela em modo normal (cancela o showFullScreen)
            self.showNormal()
        else:
            # --- VOLTAR PARA O F11 TRANSPARENTE ---
            self.tela_cheia = True
            self.btn_toggle.setText("Sair da Tela Cheia")
            self.ativar_tela_cheia_transparente()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TransparentTestApp()
    sys.exit(app.exec())