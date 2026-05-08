import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QPushButton, QLabel, QStackedWidget
)

class HomeScreen(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        layout = QVBoxLayout()
        
        titulo = QLabel("🏠 Tela Inicial")
        titulo.setStyleSheet("font-size: 30px; font-weight: bold;")
        
        btn_ir_config = QPushButton("Ir para Configurações ⚙️")
        btn_ir_config.clicked.connect(lambda: navigate_callback(1)) 
        
        layout.addWidget(titulo)
        layout.addWidget(btn_ir_config)
        self.setLayout(layout)

class SettingsScreen(QWidget):
    def __init__(self, navigate_callback):
        super().__init__()
        layout = QVBoxLayout()
        
        titulo = QLabel("⚙️ Configurações do Sistema")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #4CAF50;")
        
        btn_voltar = QPushButton("⬅️ Voltar para o Início")
        btn_voltar.clicked.connect(lambda: navigate_callback(0))
        
        layout.addWidget(titulo)
        layout.addWidget(btn_voltar)
        self.setLayout(layout)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("App com Navegação")
        self.resize(400, 300)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        tela_inicio = HomeScreen(self.mudar_tela)
        tela_configs = SettingsScreen(self.mudar_tela)

        self.stacked_widget.addWidget(tela_inicio)
        self.stacked_widget.addWidget(tela_configs) 

    def mudar_tela(self, index):
        self.stacked_widget.setCurrentIndex(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())