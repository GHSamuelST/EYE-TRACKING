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
from core import autostart
from components import ActionCard, FloatingMenu, TutorialOverlay

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
        self.modo = "normal"      # "normal" | "aiming" | "confirming"
        self.marcador_pos = None  # (x, y) do "X" est\u00e1tico na fase de confirma\u00e7\u00e3o

    def atualizar_posicao(self, x, y, progresso=0.0, modo="normal"):
        self.gaze_x = x
        self.gaze_y = y
        self.progresso_clique = progresso
        self.modo = modo
        self.update()

    def definir_marcador(self, x, y):
        """Trava o 'X' est\u00e1tico que indica onde o clique vai acontecer."""
        self.marcador_pos = (x, y)
        self.update()

    def limpar_marcador(self):
        self.marcador_pos = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # --- MARCADOR "X" EST\u00c1TICO (fase de confirma\u00e7\u00e3o) ---
        if self.marcador_pos is not None:
            mx, my = self.marcador_pos
            # Anel de progresso de confirma\u00e7\u00e3o ao redor do X
            if self.modo == "confirming" and self.progresso_clique > 0:
                pen_ring = QPen(QColor(16, 185, 129, 230))
                pen_ring.setWidth(5)
                painter.setPen(pen_ring)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                raio_ring = 42
                span = int(-360 * 16 * min(1.0, self.progresso_clique))
                painter.drawArc(
                    mx - raio_ring, my - raio_ring,
                    raio_ring * 2, raio_ring * 2,
                    90 * 16, span,
                )
            # O "X" propriamente dito
            pen_x = QPen(QColor(239, 68, 68, 255))
            pen_x.setWidth(5)
            painter.setPen(pen_x)
            s = 18
            painter.drawLine(mx - s, my - s, mx + s, my + s)
            painter.drawLine(mx - s, my + s, mx + s, my - s)

        if self.modo == "aiming":
            # --- FASE DE MIRA: crosshair + anel pulsante azul ---
            raio = 45
            # Anel externo pulsando conforme o progresso
            cor_pulso = QColor(59, 130, 246, int(80 + 120 * self.progresso_clique))
            pen = QPen(cor_pulso)
            pen.setWidth(int(3 + 4 * self.progresso_clique))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(
                self.gaze_x - raio, self.gaze_y - raio, raio * 2, raio * 2
            )

            # Anel de progresso (preenche enquanto o tempo de mira passa)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(59, 130, 246, 200)))
            raio_progresso = int(raio * self.progresso_clique * 0.6)
            painter.drawEllipse(
                self.gaze_x - raio_progresso,
                self.gaze_y - raio_progresso,
                raio_progresso * 2,
                raio_progresso * 2,
            )

            # Crosshair central
            pen_cross = QPen(QColor(59, 130, 246, 255))
            pen_cross.setWidth(2)
            painter.setPen(pen_cross)
            painter.drawLine(self.gaze_x - 12, self.gaze_y, self.gaze_x + 12, self.gaze_y)
            painter.drawLine(self.gaze_x, self.gaze_y - 12, self.gaze_x, self.gaze_y + 12)
            return

        if self.modo == "confirming":
            # --- FASE DE CONFIRMA\u00c7\u00c3O: bolinha pequena indicando onde o olhar est\u00e1 ---
            pen = QPen(QColor(59, 130, 246, 180))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 80)))
            raio = 16
            painter.drawEllipse(self.gaze_x - raio, self.gaze_y - raio, raio * 2, raio * 2)
            return

        # --- MODO NORMAL: bolinha branca com anel roxo + dwell verde ---
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
        
        self.label = SubtitleLabel("Inicializando EyeControl \nCarregando modelos e Câmera...")
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
        self.settings = QSettings("EyeControl", "EyeControl")

        # --- VARIÁVEIS DINÂMICAS DE INTERAÇÃO (Serão alteradas pelas Configs) ---
        self.alvo_atual = None
        self.tempo_inicio_foco = 0
        self.TEMPO_CLIQUE = 1.2    # Segundos focados para clicar
        self.RAIO_GRAVIDADE = 180  # Distância magnética

        # --- ESTADO DO CLIQUE (bot\u00e3o "Clicar" do menu flutuante) ---
        # Fluxo:
        #   1. dwell em "Clicar"  -> AIMING: usu\u00e1rio tem CLICK_AIM_DELAY s para mirar
        #   2. ao fim da mira     -> trava um "X" est\u00e1tico na tela (CONFIRMING)
        #   3. dwell de CLICK_CONFIRM_TIME s em cima do X -> dispara o clique
        # Para MUDAR o local, o usu\u00e1rio precisa focar o bot\u00e3o "Clicar" novamente.
        self.click_state = "idle"        # "idle" | "aiming" | "confirming"
        self.click_arm_time = 0.0
        self.CLICK_AIM_DELAY = 4.0       # segundos de mira
        self.click_target = None         # (x, y) posi\u00e7\u00e3o travada do X
        self.click_confirm_start = 0.0   # in\u00edcio do dwell de confirma\u00e7\u00e3o
        self.CLICK_CONFIRM_TIME = 3.0    # segundos de dwell para confirmar
        self.CLICK_CONFIRM_RADIUS = 130  # raio (px) em volta do X que conta como "olhando para o X"

        # Inicializa as Views
        self.home_view = HomeView(self)
        self.calib_view = CalibrationView()
        self.settings_view = SettingsView(self)
        self.apps_view = AppsView(self) # NOVA
        self.onboarding_view = OnboardingView()
        self.onboarding_view.iniciar_clicado.connect(self._on_onboarding_concluido)
        
        self.floating_menu = FloatingMenu() # NOVO (Menu lateral OS)

        # --- TUTORIAL (exibido na 1ª vez que a pessoa entra em cada passo) ---
        self.tutorial_overlay = TutorialOverlay()
        self._tutorial_on_close = None

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
        self.settings_view.iniciar_com_windows_alterado.connect(self.aplicar_iniciar_com_windows)

        # --- MOTOR DE RASTREAMENTO OCULAR (Thread Mock / Mouse) ---
        screen_geometry = QApplication.primaryScreen().geometry()
        self.motor = EyeTrackerThread(w_f=screen_geometry.width(), h_f=screen_geometry.height())
        
        self.motor.motor_pronto.connect(self.iniciar_tela_calibracao)
        self.motor.calibracao_ponto.connect(self.calib_view.atualizar_progresso)
        self.motor.fase_validacao.connect(self.calib_view.atualizar_validacao) 
        self.motor.calibracao_concluida.connect(self.iniciar_home)
        self.motor.calibracao_concluida.connect(self._salvar_calibracao)
        self.motor.coordenadas_atualizadas.connect(self.receber_coordenadas)

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

    def aplicar_iniciar_com_windows(self, ativado):
        """Liga/desliga o início automático do app com o Windows."""
        sucesso = autostart.definir(ativado)
        if not sucesso:
            # Reverte o switch caso a alteração no registro tenha falhado
            self.settings_view.definir_iniciar_com_windows(autostart.esta_ativado())
            self.home_view.atualizar_estado_autostart(autostart.esta_ativado())
            return
        self.settings.setValue("iniciar_com_windows", ativado)
        self.home_view.atualizar_estado_autostart(ativado)

    def _alternar_autostart_pelo_olhar(self):
        """Alterna o início automático a partir do card da Home (operado por olhar).

        Não usa popup de confirmação porque a Home é controlada apenas pelo
        olhar e a caixa de diálogo exigiria clique de mouse.
        """
        novo_estado = not autostart.esta_ativado()
        sucesso = autostart.definir(novo_estado)
        if not sucesso:
            novo_estado = autostart.esta_ativado()
        else:
            self.settings.setValue("iniciar_com_windows", novo_estado)

        # Sincroniza as duas interfaces com o estado real
        self.settings_view.definir_iniciar_com_windows(novo_estado)
        self.home_view.atualizar_estado_autostart(novo_estado)

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
                # Carrega como ponto de partida, mas o app SEMPRE recalibra ao abrir.
                self.motor.set_calibration_state(state)
            except (ValueError, TypeError) as e:
                print(f"[Settings] Não foi possível restaurar calibração: {e}")

        # Sincroniza o switch "iniciar com o Windows" com o estado real do registro
        self.settings_view.definir_iniciar_com_windows(autostart.esta_ativado())
        self.home_view.atualizar_estado_autostart(autostart.esta_ativado())

    def _salvar_calibracao(self):
        """Persiste o estado de calibração após uma sessão de 5 pontos completa."""
        state = self.motor.get_calibration_state()
        if state:
            self.settings.setValue("calibration", json.dumps(state))
            print("[Settings] Calibração salva.")

    def iniciar_tela_calibracao(self):
        """ Inicia ou reinicia a calibração """
        # Fecha o splash em qualquer caso (boot inicial)
        if hasattr(self, 'splash_ref') and self.splash_ref is not None:
            self.splash_ref.close()
            self.splash_ref = None

        if self.isVisible():
            self.gaze_overlay.hide()
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

        # Tutorial da Home na primeira vez
        self._maybe_show_tutorial("home")

    def receber_coordenadas(self, x, y):
        # A bolinha agora é OS-level, não precisamos mais converter para local!
        self._last_gaze_pos = (x, y)

        # --- FLUXO DE CLIQUE: MIRA + CONFIRMA\u00c7\u00c3O ---
        # Fase de mira: por CLICK_AIM_DELAY s a bolinha segue o olhar; ao fim,
        # trava um "X" est\u00e1tico no ponto olhado e passa para a confirma\u00e7\u00e3o.
        if self.click_state == "aiming":
            tempo_mira = time.time() - self.click_arm_time
            progresso = min(1.0, tempo_mira / self.CLICK_AIM_DELAY)
            self.gaze_overlay.atualizar_posicao(x, y, progresso=progresso, modo="aiming")
            if tempo_mira >= self.CLICK_AIM_DELAY:
                self.click_target = (x, y)
                self.click_confirm_start = 0.0
                self.click_state = "confirming"
                self.gaze_overlay.definir_marcador(x, y)
            return

        # Fase de confirma\u00e7\u00e3o: o X fica est\u00e1tico. Manter o olhar nele por
        # CLICK_CONFIRM_TIME s dispara o clique. Para mudar o local, o usu\u00e1rio
        # deve focar novamente o bot\u00e3o "Clicar" (reinicia a mira).
        if self.click_state == "confirming":
            tx, ty = self.click_target

            # RE-MIRAR: focar de novo o card "Clicar" reinicia a mira (move o X)
            clicar_card = getattr(self.floating_menu, 'card_clicar', None)
            if clicar_card is not None and self.floating_menu.isVisible():
                try:
                    c = clicar_card.mapToGlobal(clicar_card.rect().center())
                    if math.dist((x, y), (c.x(), c.y())) < self.RAIO_GRAVIDADE:
                        if self.alvo_atual != clicar_card:
                            self.alvo_atual = clicar_card
                            self.tempo_inicio_foco = time.time()
                        prog_rearme = min(1.0, (time.time() - self.tempo_inicio_foco) / self.TEMPO_CLIQUE)
                        self.gaze_overlay.atualizar_posicao(c.x(), c.y(), progresso=prog_rearme, modo="normal")
                        if prog_rearme >= 1.0:
                            self.click_state = "aiming"
                            self.click_arm_time = time.time()
                            self.click_target = None
                            self.click_confirm_start = 0.0
                            self.alvo_atual = None
                            self.gaze_overlay.limpar_marcador()
                        return
                except RuntimeError:
                    pass

            self.alvo_atual = None

            # Dwell em cima do X
            if math.dist((x, y), (tx, ty)) <= self.CLICK_CONFIRM_RADIUS:
                if self.click_confirm_start == 0.0:
                    self.click_confirm_start = time.time()
                progresso = min(1.0, (time.time() - self.click_confirm_start) / self.CLICK_CONFIRM_TIME)
            else:
                self.click_confirm_start = 0.0
                progresso = 0.0

            if progresso >= 1.0:
                self.click_state = "idle"
                self.click_confirm_start = 0.0
                self.click_target = None
                self.gaze_overlay.limpar_marcador()
                try:
                    pyautogui.click(tx, ty)
                except Exception as e:
                    print(f"[Click] Falha ao clicar: {e}")
                self.alvo_atual = None
                self.tempo_inicio_foco = time.time() + 0.5
                self.gaze_overlay.atualizar_posicao(x, y, progresso=0.0, modo="normal")
                return

            self.gaze_overlay.atualizar_posicao(x, y, progresso=progresso, modo="confirming")
            return

        # --- TUTORIAL ATIVO: s\u00f3 o bot\u00e3o do tutorial responde ao olhar ---
        if self.tutorial_overlay.isVisible():
            btn = self.tutorial_overlay.btn_card
            try:
                centro = btn.mapToGlobal(btn.rect().center())
            except RuntimeError:
                return
            if math.dist((x, y), (centro.x(), centro.y())) < self.RAIO_GRAVIDADE:
                if self.alvo_atual != btn:
                    self.alvo_atual = btn
                    self.tempo_inicio_foco = time.time()
                progresso = min(1.0, max(0.0, (time.time() - self.tempo_inicio_foco) / self.TEMPO_CLIQUE))
                self.gaze_overlay.atualizar_posicao(centro.x(), centro.y(), progresso=progresso, modo="normal")
                if progresso >= 1.0:
                    self._tutorial_avancar()
            else:
                self.alvo_atual = None
                self.gaze_overlay.atualizar_posicao(x, y, progresso=0.0, modo="normal")
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
            elif self.settings_view.isVisible() and hasattr(self.settings_view, 'lista_cards'):
                cards_ativos = self.settings_view.lista_cards
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
                    self._maybe_show_tutorial("settings")
                elif nome_botao == "Abrir Aplicativos":
                    self.switchTo(self.apps_view)
                    self._maybe_show_tutorial("apps")
                elif nome_botao.startswith("Iniciar com Windows"):
                    self._alternar_autostart_pelo_olhar()

                # ROTA DE VOLTA (Apps / Configurações -> Home)
                elif nome_botao == "Voltar para Home":
                    self.switchTo(self.home_view)
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

                elif nome_botao == "Clicar":
                    # Mostra o tutorial de clique na 1ª vez; depois inicia a mira
                    self.alvo_atual = None
                    self._maybe_show_tutorial("click", on_close=self._iniciar_mira_clique)
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

        # Tutorial do Modo Windows na primeira vez
        self._maybe_show_tutorial("windows")

    def sair_modo_windows(self):
        """ Retorna ao app em tela cheia """
        self.floating_menu.hide()
        self.showMaximized()
        self.switchTo(self.home_view)
        
        # Garante que a bolinha continua na frente de tudo ao voltar
        self.gaze_overlay.raise_()

    # --------------------------------------------------------------- TUTORIAL
    def _maybe_show_tutorial(self, step_key, on_close=None):
        """
        Mostra o tutorial do passo `step_key` apenas na primeira vez.
        Se já foi visto, executa `on_close` imediatamente (se houver).
        Retorna True se o tutorial foi exibido agora.
        """
        if self.settings.value(f"tutorial_{step_key}", False, type=bool):
            if on_close:
                on_close()
            return False

        self.settings.setValue(f"tutorial_{step_key}", True)
        self._tutorial_on_close = on_close
        self.alvo_atual = None
        self.tutorial_overlay.setGeometry(QApplication.primaryScreen().geometry())
        self.tutorial_overlay.mostrar_passo(step_key)
        # Mantém a bolinha do olhar visível por cima do tutorial
        self.gaze_overlay.show()
        self.gaze_overlay.raise_()
        return True

    def _tutorial_avancar(self):
        """Chamado quando o dwell sobre o botão do tutorial se completa."""
        if self.tutorial_overlay.proximo():
            # Ainda há páginas: evita re-disparo imediato
            self.alvo_atual = None
            self.tempo_inicio_foco = time.time() + 0.6
            return
        self._fechar_tutorial()

    def _fechar_tutorial(self):
        self.tutorial_overlay.hide()
        self.alvo_atual = None
        self.tempo_inicio_foco = time.time() + 0.8
        cb = self._tutorial_on_close
        self._tutorial_on_close = None
        self.gaze_overlay.raise_()
        if cb:
            cb()

    def _iniciar_mira_clique(self):
        """Inicia a fase de mira do fluxo de clique."""
        self.click_state = "aiming"
        self.click_arm_time = time.time()
        self.click_target = None
        self.click_confirm_start = 0.0
        self.gaze_overlay.limpar_marcador()
        self.alvo_atual = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    splash = SplashLoading()
    splash.show()
    
    window = EyeControlApp(splash_ref=splash)
    
    sys.exit(app.exec())