import sys
import os
import ctypes
import time
import math

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QPoint
import qtawesome as qta
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, IndeterminateProgressRing, SubtitleLabel

# Importações dos seus módulos
from views.home_view import HomeView
from views.calibration_view import CalibrationView
from core.cvml_mouse import EyeTrackerThread # Note que agora importamos do cvml
from components.action_card import ActionCard 

# Força o uso do PySide6 para bibliotecas de terceiros (qfluentwidgets, qtawesome)
os.environ["QT_API"] = "pyside6"

class GazeOverlay(QWidget):
    """ Widget invisível que fica por cima de tudo desenhando a bolinha do olhar """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.gaze_x = -100
        self.gaze_y = -100
        self.progresso_clique = 0.0 # Controla o preenchimento visual do clique (0.0 a 1.0)

    def atualizar_posicao(self, x, y, progresso=0.0):
        self.gaze_x = x
        self.gaze_y = y
        self.progresso_clique = progresso
        self.update() # Força o repaintEvent

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Borda fixa e translúcida do rastreio
        pen = QPen(QColor(79, 70, 229, 180)) # Roxo Indigo Tailwind
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
        raio = 35
        painter.drawEllipse(self.gaze_x - raio, self.gaze_y - raio, raio * 2, raio * 2)

        # Preenchimento visual animado do "Dwell Click" (Verde)
        if self.progresso_clique > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(16, 185, 129, 200))) # Verde Emerald Tailwind
            raio_interno = int(raio * self.progresso_clique)
            painter.drawEllipse(self.gaze_x - raio_interno, self.gaze_y - raio_interno, raio_interno * 2, raio_interno * 2)


class SplashLoading(QWidget):
    """ Tela de carregamento enquanto o MediaPipe/Câmera inicia na Thread """
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
        
        self.label = SubtitleLabel("Inicializando EyeControl OS\nCarregando modelos e Câmera...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.spinner.start()


class EyeControlApp(FluentWindow):
    """ Janela Principal do Sistema """
    def __init__(self, splash_ref):
        super().__init__()
        self.splash_ref = splash_ref # Guarda a ref da splash para fechá-la depois
        self.setWindowTitle("EyeControl")
        setTheme(Theme.LIGHT)

        # Agrupa o ícone na barra de tarefas do Windows
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tcc.samuel.eyecontrol.1_0")
        except: 
            pass
        
        # --- VARIÁVEIS DO DWELL CLICK (CLIQUE POR OLHAR) ---
        self.alvo_atual = None
        self.tempo_inicio_foco = 0
        self.TEMPO_CLIQUE = 1.2 # Segundos necessários olhando para um botão para ativá-lo

        # Inicializa as Views
        self.home_view = HomeView(self)
        self.calib_view = CalibrationView()
        
        # Overlay que desenha a bolinha (inicia invisível)
        self.gaze_overlay = GazeOverlay(self)
        self.gaze_overlay.hide()
        
        # Esconde a barra lateral (navigationInterface) até a calibração acabar
        self.navigationInterface.hide()

        # --- MOTOR DE RASTREAMENTO OCULAR (Thread) ---
        screen_geometry = QApplication.primaryScreen().geometry()
        self.motor = EyeTrackerThread(w_f=screen_geometry.width(), h_f=screen_geometry.height())
        
        # Conectando os sinais do motor assíncrono para a nossa UI
        self.motor.motor_pronto.connect(self.iniciar_tela_calibracao)
        self.motor.calibracao_ponto.connect(self.calib_view.atualizar_progresso)
        self.motor.fase_validacao.connect(self.calib_view.atualizar_validacao) 
        self.motor.calibracao_concluida.connect(self.iniciar_home)
        self.motor.coordenadas_atualizadas.connect(self.receber_coordenadas)

        # Inicia a thread pesada (Não trava a UI!)
        self.motor.start()

    def iniciar_tela_calibracao(self):
        """ Inicia ou reinicia a tela de calibração """
        # 1. Se veio da tela de Loading, fecha ela
        if hasattr(self, 'splash_ref') and self.splash_ref is not None:
            self.splash_ref.close()
            self.splash_ref = None  # Limpa a referência para não tentar fechar de novo
            
        # 2. Se veio da Home, esconde a Home e a bolinha do olhar
        if self.isVisible():
            self.gaze_overlay.hide()
            self.hide() 
            
        # 3. Abre a tela de calibração gigante
        self.calib_view.showFullScreen()
        
        # 4. Dá o gatilho pro motor começar a simular os 5 pontos de novo
        self.motor.iniciar_calibracao()

    def iniciar_home(self):
        """ Chamado quando a calibração de 5 pontos termina """
        self.calib_view.close() 
        
        # 1. Garante um tamanho base grande caso o Windows negue a maximização
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.resize(screen_geometry.width(), screen_geometry.height())
        
        # 2. Força a janela a abrir maximizada (Cobre tudo, mas deixa a barra de tarefas do Windows)
        self.showMaximized()
        
        self.navigationInterface.show() # Revela a sidebar
        
        # Configura a barra lateral do Fluent
        self.addSubInterface(self.home_view, qta.icon('fa5s.home', color='#111827'), 'Home')
        self.navigationInterface.addItem('Settings', qta.icon('fa5s.cog', color='#6B7280'), 'Configurações', position=NavigationItemPosition.BOTTOM)
        
        self.switchTo(self.home_view)
        
        # Habilita o rastreador visual
        self.gaze_overlay.show()
        self.gaze_overlay.raise_()

    def receber_coordenadas(self, x, y):
        """ Loop que roda a cada frame processado pelo EyeTrackerThread """
        # Converte a coordenada do monitor (Global) para a coordenada da Janela (Local)
        ponto_global = QPoint(x, y)
        local_point = self.mapFromGlobal(ponto_global)
        
        alvo_capturado = None
        menor_distancia = 180  # RAIO DE GRAVIDADE EM PIXELS

        # Evita crashes se a home view ainda não carregou os cards
        if hasattr(self.home_view, 'lista_cards') and self.home_view.isVisible():
            for card in self.home_view.lista_cards:
                try:
                    # Pega o ponto central EXATO do card na tela global
                    centro_card_global = card.mapToGlobal(card.rect().center())
                    
                    # Distância Euclidiana (Pitágoras) entre o Olhar e o Centro do Botão
                    distancia = math.dist((x, y), (centro_card_global.x(), centro_card_global.y()))
                    
                    # Captura o card se estiver dentro do raio de atração e for o mais próximo
                    if distancia < menor_distancia:
                        menor_distancia = distancia
                        alvo_capturado = card
                        centro_travado_local = self.mapFromGlobal(centro_card_global)
                except RuntimeError:
                    # Ignora cards que possam estar sendo recriados/destruídos
                    continue

        if alvo_capturado:
            # 1. ATRAÇÃO MAGNÉTICA: Força a bolinha para o centro exato do botão
            x_desenho = centro_travado_local.x()
            y_desenho = centro_travado_local.y()

            # 2. LÓGICA DE DWELL (Começa a encher a bolinha de verde)
            if self.alvo_atual != alvo_capturado:
                self.alvo_atual = alvo_capturado
                self.tempo_inicio_foco = time.time()

            tempo_focado = time.time() - self.tempo_inicio_foco
            progresso = min(1.0, max(0.0, tempo_focado / self.TEMPO_CLIQUE))

            # Atualiza a UI da bolinha (Verde enchendo)
            self.gaze_overlay.atualizar_posicao(x_desenho, y_desenho, progresso=progresso)

            # 3. EXECUÇÃO DO CLIQUE
            if progresso >= 1.0:
                nome_botao = alvo_capturado.title_label.text()
                print(f"✅ CLIQUE EXECUTADO: {nome_botao}")
                
                # --- ROTEAMENTO DAS AÇÕES ---
                if nome_botao == "Começar Calibração":
                    self.iniciar_tela_calibracao()
                    
                elif nome_botao == "Iniciar com Windows":
                    # Faremos a lógica de Registro do Windows depois
                    print("Lógica do Windows em breve!")
                    
                elif nome_botao == "Configurações":
                    # Faremos a tela de configs depois
                    print("Abrindo configurações!")

                # ----------------------------

                # Tempo de espera (Cooldown) para não clicar várias vezes
                self.tempo_inicio_foco = time.time() + 1.5 
                
                # Limpa o alvo atual e zera a bolinha para não bugar o visual
                self.alvo_atual = None 
                self.gaze_overlay.atualizar_posicao(x_desenho, y_desenho, progresso=0.0)
        else:
            # Fora da gravidade de qualquer botão: Movimento Livre normal (Bolinha vazia)
            self.alvo_atual = None
            self.gaze_overlay.atualizar_posicao(local_point.x(), local_point.y(), progresso=0.0)

    def resizeEvent(self, e):
        """ Garante que o painel de desenho da bolinha acompanhe o tamanho da janela """
        super().resizeEvent(e)
        if hasattr(self, 'gaze_overlay'):
            self.gaze_overlay.resize(self.size())

    def closeEvent(self, event):
        """ Desliga a câmera e encerra a thread de forma limpa ao fechar o app """
        if hasattr(self, 'motor'):
            self.motor.parar()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Inicia a Splash Screen logo de cara
    splash = SplashLoading()
    splash.show()
    
    # Inicia o App em background (ele fechará a splash via sinal quando o motor carregar)
    window = EyeControlApp(splash_ref=splash)
    
    sys.exit(app.exec())