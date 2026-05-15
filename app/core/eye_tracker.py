import cv2
import mediapipe as mp
import numpy as np
import time
import math
import statistics
from PySide6.QtCore import QThread, Signal

def mapear_eixo(valor_atual, val_calib_a, val_calib_b, tela_a, tela_b, limite_min, limite_max):
    if val_calib_a == val_calib_b: 
        return tela_a
    porcentagem = (valor_atual - val_calib_a) / (val_calib_b - val_calib_a)
    pos_tela = tela_a + porcentagem * (tela_b - tela_a)
    return max(limite_min, min(limite_max, pos_tela))

class EyeTrackerThread(QThread):
    # Sinais para comandar a Interface Gráfica
    motor_pronto = Signal()
    calibracao_ponto = Signal(int, float)
    fase_validacao = Signal(int) # Emite os segundos restantes da validação
    calibracao_concluida = Signal()
    coordenadas_atualizadas = Signal(int, int)

    def __init__(self, largura_tela, altura_tela):
        super().__init__()
        self.rodando = True
        self.estado = 'INIT'
        self.w_f = largura_tela
        self.h_f = altura_tela

        self.ponto_atual = 0
        self.pontos_alvo = [(0.5, 0.5), (0.1, 0.05), (0.9, 0.05), (0.1, 0.95), (0.9, 0.95)]
        
        self.buffer_h, self.buffer_v = [], []
        self.mapa_calibrado = [] 
        self.h_esq, self.h_dir, self.v_cima, self.v_baixo = 0, 1, 0, 1 
        
        self.dwell_timer = 0
        self.TEMPO_FIXACAO = 3.5 
        self.TEMPO_VALIDACAO = 6.0 

        self.alvo_x, self.alvo_y = self.w_f / 2, self.h_f / 2
        self.cursor_x, self.cursor_y = self.w_f / 2, self.h_f / 2
        self.LIMITE_TREMOR = 18       
        self.FATOR_SUAVIZACAO = 0.12  

        self.latencias = []
        self.coordenadas_validacao = []

    def run(self):
        model_path = 'app/core/face_landmarker.task'
        cap = cv2.VideoCapture(0)
        
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=0.8,
            min_face_presence_confidence=0.8,
            output_face_blendshapes=False
        )
        detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)

        self.motor_pronto.emit()

        while self.rodando and cap.isOpened():
            start_time = time.time()
            ret, frame = cap.read()
            if not ret: continue
            
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            results = detector.detect(mp_image)

            if results.face_landmarks and self.estado != 'INIT':
                land = results.face_landmarks[0]
                
                p_iris = np.array([land[473].x, land[473].y])
                p_in = np.array([land[362].x, land[362].y])
                p_out = np.array([land[263].x, land[263].y])
                p_up = np.array([land[386].x, land[386].y])
                p_down = np.array([land[374].x, land[374].y])
                
                dist_horizontal_total = np.linalg.norm(p_out - p_in)
                dist_vertical_total = np.linalg.norm(p_down - p_up)
                
                # --- NOVO: FILTRO ANTI-PULOS (BLINK REJECTION) ---
                # Calcula a abertura do olho. Se for muito pequena, é uma piscada/falha.
                abertura_olho = dist_vertical_total / dist_horizontal_total if dist_horizontal_total > 0 else 0
                
                if abertura_olho < 0.15: # O olho está muito fechado
                    # Pula este frame e mantém a bolinha onde estava
                    continue
                # -------------------------------------------------
                
                rh = np.linalg.norm(p_iris - p_in) / dist_horizontal_total if dist_horizontal_total > 0 else 0.5
                p_center = (p_up + p_down) / 2.0
                rv = (p_iris[1] - p_center[1]) / dist_vertical_total if dist_vertical_total > 0 else 0
                
                cur_h, cur_v = rh, rv

                if self.estado == 'CALIBRACAO':
                    if self.dwell_timer == 0: self.dwell_timer = time.time()
                    decorrido = time.time() - self.dwell_timer
                    
                    if decorrido > 0.7: 
                        self.buffer_h.append(cur_h)
                        self.buffer_v.append(cur_v)

                    progresso = min(1.0, decorrido / self.TEMPO_FIXACAO)
                    self.calibracao_ponto.emit(self.ponto_atual, progresso)

                    if decorrido >= self.TEMPO_FIXACAO:
                        self.mapa_calibrado.append((np.median(self.buffer_h), np.median(self.buffer_v)))
                        self.ponto_atual += 1
                        self.dwell_timer = 0
                        self.buffer_h, self.buffer_v = [], []
                        
                        if self.ponto_atual >= len(self.pontos_alvo):
                            self.h_esq = (self.mapa_calibrado[1][0] + self.mapa_calibrado[3][0]) / 2.0
                            self.h_dir = (self.mapa_calibrado[2][0] + self.mapa_calibrado[4][0]) / 2.0
                            self.v_cima = (self.mapa_calibrado[1][1] + self.mapa_calibrado[2][1]) / 2.0
                            self.v_baixo = (self.mapa_calibrado[3][1] + self.mapa_calibrado[4][1]) / 2.0
                            
                            self.estado = 'VALIDACAO' 
                            self.dwell_timer = 0
                            self.coordenadas_validacao = []
                            self.latencias = []

                elif self.estado in ['VALIDACAO', 'LIVRE']:
                    pos_x_bruta = mapear_eixo(cur_h, self.h_esq, self.h_dir, self.w_f * 0.1, self.w_f * 0.9, 0, self.w_f)
                    pos_y_bruta = mapear_eixo(cur_v, self.v_cima, self.v_baixo, self.h_f * 0.05, self.h_f * 0.95, 0, self.h_f)

                    dist_movimento = math.dist((pos_x_bruta, pos_y_bruta), (self.alvo_x, self.alvo_y))
                    if dist_movimento > self.LIMITE_TREMOR:
                        self.alvo_x, self.alvo_y = pos_x_bruta, pos_y_bruta

                    self.cursor_x += (self.alvo_x - self.cursor_x) * self.FATOR_SUAVIZACAO
                    self.cursor_y += (self.alvo_y - self.cursor_y) * self.FATOR_SUAVIZACAO

                    if self.estado == 'VALIDACAO':
                        if self.dwell_timer == 0: self.dwell_timer = time.time()
                        decorrido = time.time() - self.dwell_timer

                        tempo_restante = max(0, int(self.TEMPO_VALIDACAO - decorrido))
                        self.fase_validacao.emit(tempo_restante)

                        if decorrido > 0.5: 
                            self.coordenadas_validacao.append((self.cursor_x, self.cursor_y))
                        
                        if decorrido >= self.TEMPO_VALIDACAO:
                            tx, ty = int(self.w_f * 0.5), int(self.h_f * 0.5)
                            erros_euclidianos = [math.dist((cx, cy), (tx, ty)) for cx, cy in self.coordenadas_validacao]
                            acuracia_media_px = sum(erros_euclidianos) / len(erros_euclidianos) if erros_euclidianos else 0
                            
                            jitter_x = statistics.stdev([c[0] for c in self.coordenadas_validacao]) if len(self.coordenadas_validacao) > 1 else 0
                            jitter_y = statistics.stdev([c[1] for c in self.coordenadas_validacao]) if len(self.coordenadas_validacao) > 1 else 0
                            
                            latencia_media_ms = (sum(self.latencias) / len(self.latencias)) if self.latencias else 0
                            fps_medio = 1000 / latencia_media_ms if latencia_media_ms > 0 else 0

                            print("\n" + "="*40)
                            print("RESULTADOS DA VALIDAÇÃO (BACKGROUND)")
                            print("="*40)
                            print(f"Erro Médio (Acurácia): {acuracia_media_px:.2f} pixels")
                            print(f"Estabilidade X (Jitter): {jitter_x:.2f} px")
                            print(f"Estabilidade Y (Jitter): {jitter_y:.2f} px")
                            print(f"FPS Médio: {fps_medio:.2f}")
                            print("="*40 + "\n")

                            self.estado = 'LIVRE'
                            self.calibracao_concluida.emit()

                    elif self.estado == 'LIVRE':
                        self.coordenadas_atualizadas.emit(int(self.cursor_x), int(self.cursor_y))

            end_time = time.time()
            if self.estado == 'VALIDACAO':
                self.latencias.append((end_time - start_time) * 1000)
            
            QThread.msleep(10)

        cap.release()

    def iniciar_calibracao(self):
        self.estado = 'CALIBRACAO'
        self.ponto_atual = 0
        self.mapa_calibrado = []
        self.dwell_timer = 0

    def parar(self):
        self.rodando = False
        self.wait()