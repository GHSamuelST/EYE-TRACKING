import time
import pyautogui
from PySide6.QtCore import QThread, Signal

class EyeTrackerThread(QThread):
    """
    VERSÃO MOCK (SIMULADA) DO RASTREADOR.
    Usa o mouse real do usuário para simular para onde o olho estaria olhando.
    Ideal para testar UI/UX sem precisar de webcam ou iluminação perfeita.
    """
    # Os sinais são EXATAMENTE os mesmos do modelo real. 
    # O main.py não faz ideia de que isso é um simulador.
    motor_pronto = Signal()
    coordenadas_atualizadas = Signal(int, int)
    calibracao_ponto = Signal(int, float) 
    fase_validacao = Signal(int)          
    calibracao_concluida = Signal()

    def __init__(self, w_f=1920, h_f=1080):
        super().__init__()
        self.w_f = w_f
        self.h_f = h_f
        self.rodando = True
        
        # Estado da Calibração
        self.em_calibracao = False
        self.ponto_calib_atual = 0
        self.tempo_inicio_ponto = 0
        self.TEMPO_POR_PONTO = 1.5 # Deixei mais rápido (1.5s) para facilitar os testes

    def iniciar_calibracao(self):
        self.em_calibracao = True
        self.ponto_calib_atual = 0
        self.tempo_inicio_ponto = time.time()

    def parar(self):
        self.rodando = False
        self.wait()

    def run(self):
        """ Loop principal (Falso processamento de imagem) """
        
        # Simula o tempo que o MediaPipe levaria para carregar os modelos pesados
        time.sleep(2.0)
        
        # Avisa a Splash Screen que "A câmera ligou"
        self.motor_pronto.emit()

        # Loop infinito a ~60 FPS
        while self.rodando:
            current_time = time.time()

            # ========================================================
            # 1. MODO CALIBRAÇÃO (Simulação automática)
            # ========================================================
            if self.em_calibracao:
                tempo_focado = current_time - self.tempo_inicio_ponto
                progresso = min(1.0, tempo_focado / self.TEMPO_POR_PONTO)
                
                # Fase de Calibração (Pontos 1 a 5)
                if self.ponto_calib_atual < 5:
                    self.calibracao_ponto.emit(self.ponto_calib_atual, progresso)
                    
                    if progresso >= 1.0:
                        self.ponto_calib_atual += 1
                        self.tempo_inicio_ponto = current_time
                
                # Fase de Validação (Teste final no centro)
                elif self.ponto_calib_atual == 5:
                    segundos_restantes = int(3.0 - tempo_focado) + 1
                    self.fase_validacao.emit(segundos_restantes)
                    
                    if tempo_focado >= 3.0:
                        self.em_calibracao = False
                        self.calibracao_concluida.emit()
            
            # ========================================================
            # 2. MODO NORMAL (Rastreamento "Ocular")
            # ========================================================
            else:
                # O TRUQUE: Pegamos a coordenada real do mouse físico do Windows!
                mouse_x, mouse_y = pyautogui.position()
                
                # Emitimos para o main.py como se fosse o olhar processado pelo OpenCV
                self.coordenadas_atualizadas.emit(mouse_x, mouse_y)

            # Pausa de ~16ms para rodar a 60 FPS sem fritar a CPU
            time.sleep(0.016)