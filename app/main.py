import sys
import os
import ctypes
import time
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QPoint
import qtawesome as qta
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, IndeterminateProgressRing, SubtitleLabel
import math

from views.home_view import HomeView
from views.calibration_view import CalibrationView
from core.eye_tracker import EyeTrackerThread
from components.action_card import ActionCard # Necessário para detectar colisão

os.environ["QT_API"] = "pyside6"

class GazeOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.gaze_x = -100
        self.gaze_y = -100
        self.progresso_clique = 0.0 # Controla o preenchimento visual do clique

    def atualizar_posicao(self, x, y, progresso=0.0):
        self.gaze_x = x
        self.gaze_y = y
        self.progresso_clique = progresso
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Borda fixa do rastreio
        pen = QPen(QColor(79, 70, 229, 180)) 
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
        raio = 35
        painter.drawEllipse(self.gaze_x - raio, self.gaze_y - raio, raio * 2, raio * 2)

        # Preenchimento visual do "Dwell Click" (Botão sendo pressionado)
        if self.progresso_clique > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(16, 185, 129, 200))) # Verde
            raio_interno = int(raio * self.progresso_clique)
            painter.drawEllipse(self.gaze_x - raio_interno, self.gaze_y - raio_interno, raio_interno * 2, raio_interno * 2)

class SplashLoading(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(400, 300)
        self.setStyleSheet("background-color: #F8F9FA; border-radius: 20px; border: 1px solid #E5E7EB;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spinner = IndeterminateProgressRing(self)
        self.spinner.setFixedSize(50, 50)
        self.spinner.setStrokeWidth(5)
        
        self.label = SubtitleLabel("Inicializando EyeControl OS\nCarregando modelos de IA...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.spinner.start()

class EyeControlApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EyeControl OS")
        setTheme(Theme.LIGHT)

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tcc.samuel.eyecontrol.1_0")
        except: 
            pass
        
        # --- VARIÁVEIS DO CLIQUE MAGNÉTICO ---
        self.alvo_atual = None
        self.tempo_inicio_foco = 0
        self.TEMPO_CLIQUE = 1.2 # Segundos necessários para clicar em um botão

        self.home_view = HomeView(self)
        self.calib_view = CalibrationView()
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.hide()
        
        self.navigationInterface.hide()

        self.motor = EyeTrackerThread(1920, 1080)
        self.motor.motor_pronto.connect(self.iniciar_tela_calibracao)
        self.motor.calibracao_ponto.connect(self.calib_view.atualizar_progresso)
        self.motor.fase_validacao.connect(self.calib_view.atualizar_validacao) # Nova conexão
        self.motor.calibracao_concluida.connect(self.iniciar_home)
        self.motor.coordenadas_atualizadas.connect(self.receber_coordenadas)

        self.motor.start()

    def iniciar_tela_calibracao(self):
        splash.close() 
        screen_geometry = QApplication.primaryScreen().geometry()
        self.motor.w_f = screen_geometry.width()
        self.motor.h_f = screen_geometry.height()

        self.calib_view.showFullScreen()
        self.motor.iniciar_calibracao()

    def iniciar_home(self):
        self.calib_view.close() 
        self.showMaximized() 
        self.navigationInterface.show() 
        
        self.addSubInterface(self.home_view, qta.icon('fa5s.home', color='#111827'), 'Home')
        self.navigationInterface.addItem('Settings', qta.icon('fa5s.cog', color='#6B7280'), 'Configurações', position=NavigationItemPosition.BOTTOM)
        
        self.switchTo(self.home_view)
        
        self.gaze_overlay.show()
        self.gaze_overlay.raise_()

    def receber_coordenadas(self, x, y):
        # Converte as coordenadas cruas para locais
        ponto_global = QPoint(x, y)
        local_point = self.mapFromGlobal(ponto_global)
        
        alvo_capturado = None
        menor_distancia = 350  # RAIO DE GRAVIDADE (Em pixels. Aumente se quiser que puxe de mais longe)

        # Procura qual é o botão mais próximo da bolinha usando a lista que criamos
        if hasattr(self.home_view, 'lista_cards'):
            for card in self.home_view.lista_cards:
                # Pega o ponto central EXATO do card na tela global
                centro_card_global = card.mapToGlobal(card.rect().center())
                
                # Calcula a distância entre o seu olhar e o centro do botão
                distancia = math.dist((x, y), (centro_card_global.x(), centro_card_global.y()))
                
                # Se a bolinha entrou na gravidade do botão e é o mais próximo
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    alvo_capturado = card
                    centro_travado_local = self.mapFromGlobal(centro_card_global)

        if alvo_capturado:
            # 1. ATRAÇÃO MAGNÉTICA: Força a bolinha para o centro do botão
            x_desenho = centro_travado_local.x()
            y_desenho = centro_travado_local.y()

            # 2. LÓGICA DE DWELL (Preenchimento)
            if self.alvo_atual != alvo_capturado:
                self.alvo_atual = alvo_capturado
                self.tempo_inicio_foco = time.time()

            tempo_focado = time.time() - self.tempo_inicio_foco
            progresso = min(1.0, tempo_focado / self.TEMPO_CLIQUE)

            self.gaze_overlay.atualizar_posicao(x_desenho, y_desenho, progresso=progresso)

            # 3. EXECUÇÃO DO CLIQUE
            if progresso >= 1.0:
                print(f"✅ CLIQUE EXECUTADO: {alvo_capturado.title_label.text()}")
                # Tempo de espera para não clicar no botão duas vezes seguidas
                self.tempo_inicio_foco = time.time() + 1.5 
        else:
            # Fora da gravidade de qualquer botão: Movimento Livre normal
            self.alvo_atual = None
            self.gaze_overlay.atualizar_posicao(local_point.x(), local_point.y(), progresso=0.0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'gaze_overlay'):
            self.gaze_overlay.resize(self.size())

    def closeEvent(self, event):
        self.motor.parar()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashLoading()
    splash.show()
    
    window = EyeControlApp()
    
    sys.exit(app.exec())