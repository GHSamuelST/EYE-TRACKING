import sys
import os
import ctypes
import time
import math
import json

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon, QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QPoint, QSettings
import qtawesome as qta
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, IndeterminateProgressRing, SubtitleLabel
import subprocess
import pyautogui

# Importações limpas graças aos nossos arquivos __init__.py
from views import HomeView, CalibrationView, SettingsView, AppsView, OnboardingView
from core import EyeTrackerThread
from components import ActionCard, FloatingMenu, StatusIndicator

os.environ["QT_API"] = "pyside6"

class GazeOverlay(QWidget):
    """ Widget invisível que desenha a bolinha do olhar """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- O SEGREDO DO CLIQUE ATRAVESSAR (OS-LEVEL) ---
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput # <-- Esta flag mágica libera o mouse físico!
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.gaze_x = -100
        self.gaze_y = -100
        self.progresso_clique = 0.0

    def atualizar_posicao(self, x, y, progresso=0.0):
        self.gaze_x = x
        self.gaze_y = y
        self.progresso_clique = progresso
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor(79, 70, 229, 180)) 
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 120)))
        raio = 35
        painter.drawEllipse(self.gaze_x - raio, self.gaze_y - raio, raio * 2, raio * 2)

        if self.progresso_clique > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(16, 185, 129, 200))) 
            raio_interno = int(raio * self.progresso_clique)
            painter.drawEllipse(self.gaze_x - raio_interno, self.gaze_y - raio_interno, raio_interno * 2, raio_interno * 2)


class SplashLoading(QWidget):
    """ Tela de carregamento do sistema """
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
        self.splash_ref = splash_ref
        self.setWindowTitle("EyeControl OS")
        setTheme(Theme.LIGHT)

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("tcc.samuel.eyecontrol.1_0")
        except: 
            pass

        # --- ARMAZENAMENTO PERSISTENTE (sliders + calibração) ---
        self.settings = QSettings("EyeControl", "EyeControlOS")

        # --- VARIÁVEIS DINÂMICAS DE INTERAÇÃO (Serão alteradas pelas Configs) ---
        self.alvo_atual = None
        self.tempo_inicio_foco = 0
        self.TEMPO_CLIQUE = 1.2    # Segundos focados para clicar
        self.RAIO_GRAVIDADE = 180  # Distância magnética

        # --- ESTADO DO CLIQUE ARMADO (botão "Clicar" do menu flutuante) ---
        # Quando o usuário olha o botão "Clicar" e completa o dwell,
        # entramos em modo armado por CLICK_AIM_DELAY segundos. Durante
        # esse tempo, ignoramos o magnetismo dos cards e disparamos um
        # pyautogui.click() na posição final do olhar.
        self.click_armed = False
        self.click_arm_time = 0.0
        self.CLICK_AIM_DELAY = 1.5

        # Inicializa as Views
        self.home_view = HomeView(self)
        self.calib_view = CalibrationView()
        self.settings_view = SettingsView(self)
        self.apps_view = AppsView(self) # NOVA
        self.onboarding_view = OnboardingView()
        self.onboarding_view.iniciar_clicado.connect(self._on_onboarding_concluido)
        
        self.floating_menu = FloatingMenu() # NOVO (Menu lateral OS)

        # --- Indicador de status do rastreamento (OS-level) ---
        self.status_indicator = StatusIndicator()
        screen_geo = QApplication.primaryScreen().geometry()
        self.status_indicator.move(screen_geo.width() - self.status_indicator.width() - 20, 20)
        self.status_indicator.hide()

        # Overlay da bolinha (Agora OS-level)
        self.gaze_overlay = GazeOverlay(None)
        screen_geo = QApplication.primaryScreen().geometry()
        self.gaze_overlay.setGeometry(screen_geo) # Cobre a tela toda
        self.gaze_overlay.hide()
        
        self.navigationInterface.hide()

        # Conecta os Sinais da Tela de Configurações
        self.settings_view.voltar_clicado.connect(lambda: self.switchTo(self.home_view))
        self.settings_view.config_atualizada.connect(self.aplicar_configuracoes)
        self.settings_view.recalibrar_clicado.connect(self.iniciar_tela_calibracao)

        # --- MOTOR DE RASTREAMENTO OCULAR (Thread Mock / Mouse) ---
        screen_geometry = QApplication.primaryScreen().geometry()
        self.motor = EyeTrackerThread(w_f=screen_geometry.width(), h_f=screen_geometry.height())
        
        self.motor.motor_pronto.connect(self.iniciar_tela_calibracao)
        self.motor.calibracao_ponto.connect(self.calib_view.atualizar_progresso)
        self.motor.fase_validacao.connect(self.calib_view.atualizar_validacao) 
        self.motor.calibracao_concluida.connect(self.iniciar_home)
        self.motor.calibracao_concluida.connect(self._salvar_calibracao)
        self.motor.coordenadas_atualizadas.connect(self.receber_coordenadas)
        self.motor.face_detectada.connect(self._on_face_detectada)

        # Restaura sliders salvos antes de a thread começar a rodar
        self._restaurar_configuracoes_salvas()

        self.motor.start()

    def aplicar_configuracoes(self, configs):
        """ Atualiza o app baseado nos sliders arrastados na SettingsView """
        self.TEMPO_CLIQUE = configs["dwell_time"]
        self.RAIO_GRAVIDADE = configs["gravidade"]

        # Atualiza o motor se o método existir na Thread
        if hasattr(self.motor, 'atualizar_sensibilidade'):
            self.motor.atualizar_sensibilidade(configs["sens_x"], configs["sens_y"])

        # Persiste
        self.settings.setValue("sliders", json.dumps(configs))

    def _restaurar_configuracoes_salvas(self):
        """Recarrega sliders e calibração do disco (se existirem)."""
        sliders_raw = self.settings.value("sliders", None)
        if sliders_raw:
            try:
                configs = json.loads(sliders_raw) if isinstance(sliders_raw, str) else sliders_raw
                self.settings_view.carregar_configuracoes(configs)
            except (ValueError, TypeError) as e:
                print(f"[Settings] Não foi possível restaurar sliders: {e}")

        calib_raw = self.settings.value("calibration", None)
        if calib_raw:
            try:
                state = json.loads(calib_raw) if isinstance(calib_raw, str) else calib_raw
                if self.motor.set_calibration_state(state):
                    self._calibracao_carregada_do_disco = True
                    print("[Settings] Calibração restaurada do disco.")
            except (ValueError, TypeError) as e:
                print(f"[Settings] Não foi possível restaurar calibração: {e}")

    def _salvar_calibracao(self):
        """Persiste o estado de calibração após uma sessão de 5 pontos completa."""
        state = self.motor.get_calibration_state()
        if state:
            self.settings.setValue("calibration", json.dumps(state))
            print("[Settings] Calibração salva.")

    def _on_face_detectada(self, presente):
        """Atualiza o pill de status sempre que o motor ganha/perde rastreamento."""
        if not self.status_indicator.isVisible():
            return
        self.status_indicator.set_state("tracking" if presente else "no_face")

    def iniciar_tela_calibracao(self):
        """ Inicia ou reinicia a calibração """
        # Fecha o splash em qualquer caso (boot inicial)
        if hasattr(self, 'splash_ref') and self.splash_ref is not None:
            self.splash_ref.close()
            self.splash_ref = None

        # Se uma calibração foi restaurada do disco no boot, pula direto pra Home
        if getattr(self, "_calibracao_carregada_do_disco", False) and not self.isVisible() and not self.calib_view.isVisible():
            self._calibracao_carregada_do_disco = False
            self.iniciar_home()
            return

        if self.isVisible():
            self.gaze_overlay.hide()
            self.status_indicator.hide()
            self.hide()

        # --- Primeira execução: mostra onboarding antes da calibração ---
        if not self.settings.value("first_run_done", False, type=bool):
            self.onboarding_view.showFullScreen()
            return

        self.calib_view.showFullScreen()
        self.motor.iniciar_calibracao()

    def _on_onboarding_concluido(self):
        """Usuário clicou em 'Iniciar Calibração' na tela de boas-vindas."""
        self.settings.setValue("first_run_done", True)
        self.onboarding_view.close()
        self.calib_view.showFullScreen()
        self.motor.iniciar_calibracao()

    def iniciar_home(self):
        """ Chamado quando a calibração termina """
        self.calib_view.close() 
        
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.resize(screen_geometry.width(), screen_geometry.height())
        self.showMaximized()
        
        self.navigationInterface.show() 
        
        # --- REGISTRO DAS TELAS NA BARRA LATERAL ---
        # Evita registrar duas vezes ao recalibrar
        if self.home_view not in self.navigationInterface.findChildren(type(self.home_view)):
            try:
                self.addSubInterface(self.home_view, qta.icon('fa5s.home', color='#111827'), 'Home')
                self.addSubInterface(self.apps_view, qta.icon('fa5s.th-large', color='#111827'), 'Aplicativos')
                self.addSubInterface(self.settings_view, qta.icon('fa5s.cog', color='#111827'), 'Configurações', position=NavigationItemPosition.BOTTOM)
            except Exception:
                pass
        
        self.switchTo(self.home_view)
        
        self.gaze_overlay.show()
        self.gaze_overlay.raise_()

        # Mostra o pill de status (verde/amarelo conforme rosto detectado)
        self.status_indicator.set_state("tracking")
        self.status_indicator.show()
        self.status_indicator.raise_()

    def receber_coordenadas(self, x, y):
        # A bolinha agora é OS-level, não precisamos mais converter para local!

        # --- MODO CLIQUE ARMADO ---
        # Enquanto armado: ignora cards e mostra contagem regressiva visual.
        # Ao expirar o delay de mira, dispara um clique real onde o olhar está.
        if self.click_armed:
            tempo_armado = time.time() - self.click_arm_time
            progresso = min(1.0, tempo_armado / self.CLICK_AIM_DELAY)
            self.gaze_overlay.atualizar_posicao(x, y, progresso=progresso)
            if tempo_armado >= self.CLICK_AIM_DELAY:
                self.click_armed = False
                try:
                    pyautogui.click(x, y)
                except Exception as e:
                    print(f"[Click] Falha ao clicar: {e}")
                self.alvo_atual = None
                self.tempo_inicio_foco = time.time() + 0.5
                self.gaze_overlay.atualizar_posicao(x, y, progresso=0.0)
            return

        alvo_capturado = None
        menor_distancia = self.RAIO_GRAVIDADE

        # --- RADAR DE CARDS DINÂMICO ---
        cards_ativos = []
        if self.isVisible(): # Se o EyeControl estiver em tela cheia
            if self.home_view.isVisible() and hasattr(self.home_view, 'lista_cards'):
                cards_ativos = self.home_view.lista_cards
            elif self.apps_view.isVisible() and hasattr(self.apps_view, 'lista_cards'):
                cards_ativos = self.apps_view.lista_cards
        else: # Se o EyeControl estiver oculto (Modo Windows)
            if self.floating_menu.isVisible():
                cards_ativos = self.floating_menu.lista_cards

        for card in cards_ativos:
            try:
                centro_card_global = card.mapToGlobal(card.rect().center())
                distancia = math.dist((x, y), (centro_card_global.x(), centro_card_global.y()))
                
                if distancia < menor_distancia:
                    menor_distancia = distancia
                    alvo_capturado = card
                    centro_travado_global = centro_card_global # Usamos global direto
            except RuntimeError:
                continue

        if alvo_capturado:
            # 1. ATRAÇÃO MAGNÉTICA
            x_desenho = centro_travado_global.x()
            y_desenho = centro_travado_global.y()

            # 2. LÓGICA DE DWELL (Preenchimento Verde)
            if self.alvo_atual != alvo_capturado:
                self.alvo_atual = alvo_capturado
                self.tempo_inicio_foco = time.time()

            tempo_focado = time.time() - self.tempo_inicio_foco
            progresso = min(1.0, max(0.0, tempo_focado / self.TEMPO_CLIQUE))

            self.gaze_overlay.atualizar_posicao(x_desenho, y_desenho, progresso=progresso)
            
            # 3. ROTEADOR DE CLIQUES
            if progresso >= 1.0:
                nome_botao = alvo_capturado.title_label.text()
                
                # ROTAS DA HOME
                if nome_botao == "Começar Calibração":
                    self.iniciar_tela_calibracao()
                elif nome_botao == "Configurações":
                    self.switchTo(self.settings_view)
                elif nome_botao == "Abrir Aplicativos":
                    self.switchTo(self.apps_view)
                
                # ROTAS DE APPS (Magia do OS)
                elif nome_botao == "Navegador Web":
                    subprocess.Popen("start msedge", shell=True) # Abre o Edge
                    self.entrar_modo_windows()
                elif nome_botao == "Arquivos":
                    subprocess.Popen("explorer") # Abre as pastas
                    self.entrar_modo_windows()
                    
                # ROTAS DO MENU FLUTUANTE
                elif nome_botao == "Rolar para Cima":
                    pyautogui.press('pageup')   # Tecla Page Up (muito mais confiável)
                    
                elif nome_botao == "Rolar para Baixo":
                    pyautogui.press('pagedown') # Tecla Page Down
                    
                elif nome_botao == "Voltar Página":
                    pyautogui.press('browserback') # Usa press em vez de hotkey

                elif nome_botao == "Anterior":
                    pyautogui.press('left')  # YouTube/players: vídeo anterior / volta

                elif nome_botao == "Próximo":
                    pyautogui.press('right')  # YouTube/players: próximo vídeo / avança

                elif nome_botao == "Clicar":
                    # Arma um clique: usuário tem CLICK_AIM_DELAY segundos para mirar
                    self.click_armed = True
                    self.click_arm_time = time.time()
                    self.alvo_atual = None
                    return
                    
                elif nome_botao == "Tela Cheia (Home)":
                    self.sair_modo_windows()
                    
                elif nome_botao == "Fechar Aplicativo":
                    pyautogui.hotkey('alt', 'f4') # Atalho mestre do Windows
                    
                self.tempo_inicio_foco = time.time() + 1.5 
                self.alvo_atual = None 
                self.gaze_overlay.atualizar_posicao(x_desenho, y_desenho, progresso=0.0)
        else:
            self.alvo_atual = None
            self.gaze_overlay.atualizar_posicao(x, y, progresso=0.0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'gaze_overlay'):
            self.gaze_overlay.resize(self.size())

    def closeEvent(self, event):
        if hasattr(self, 'motor'):
            self.motor.parar()
        super().closeEvent(event)
    
    def entrar_modo_windows(self):
        """ Esconde o app principal e mostra apenas o menu lateral """
        self.hide() # Fica totalmente transparente para o Windows
        
        # Menu agora cobre a tela inteira: cards são ancorados nas bordas/cantos
        screen_geo = QApplication.primaryScreen().geometry()
        self.floating_menu.setGeometry(screen_geo)
        self.floating_menu.show()
        
        # --- A MÁGICA DA CAMADA (Z-ORDER) ---
        # Isso arranca a bolinha de trás do menu e joga para a frente de tudo!
        self.gaze_overlay.raise_()
        self.status_indicator.raise_()
        
    def sair_modo_windows(self):
        """ Retorna ao app em tela cheia """
        self.floating_menu.hide()
        self.showMaximized()
        self.switchTo(self.home_view)
        
        # Garante que a bolinha continua na frente de tudo ao voltar
        self.gaze_overlay.raise_()
        self.status_indicator.raise_()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashLoading()
    splash.show()
    
    window = EyeControlApp(splash_ref=splash)
    
    sys.exit(app.exec())