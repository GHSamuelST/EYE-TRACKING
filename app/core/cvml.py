import cv2
import mediapipe as mp
import numpy as np
import time
import math
import statistics

# --- FUNÇÃO DE MAPEAMENTO PARA CORRIGIR EIXOS INVERTIDOS ---
def mapear_eixo(valor_atual, val_calib_a, val_calib_b, tela_a, tela_b, limite_min, limite_max):
    if val_calib_a == val_calib_b: 
        return tela_a
    porcentagem = (valor_atual - val_calib_a) / (val_calib_b - val_calib_a)
    pos_tela = tela_a + porcentagem * (tela_b - tela_a)
    return max(limite_min, min(limite_max, pos_tela))

def main():
    model_path = 'app\\core\\face_landmarker.task'
    cap = cv2.VideoCapture(0)
    
    # Resolução base recomendada
    LARGURA_TELA = 1280
    ALTURA_TELA = 720
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, LARGURA_TELA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTURA_TELA)
    
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.8,
        min_face_presence_confidence=0.8,
        output_face_blendshapes=True
    )
    detector = mp.tasks.vision.FaceLandmarker.create_from_options(options)

    # --- CONFIGURAÇÃO DE TELA CHEIA E BOTÃO FECHAR ---
    cv2.namedWindow('Sistema de Eye Tracking', cv2.WINDOW_NORMAL)
    cv2.setWindowProperty('Sistema de Eye Tracking', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    fechar_app = False
    def gerenciar_clique(event, x, y, flags, param):
        nonlocal fechar_app
        if event == cv2.EVENT_LBUTTONDOWN:
            # Área do botão fechar no canto superior direito
            if x >= LARGURA_TELA - 180 and y <= 80:
                fechar_app = True

    cv2.setMouseCallback('Sistema de Eye Tracking', gerenciar_clique)

    # --- VARIÁVEIS DE ESTADO E CALIBRAÇÃO ---
    estado = 'INICIO' 
    ponto_atual = 0
    pontos_alvo = [(0.5, 0.5), (0.1, 0.05), (0.9, 0.05), (0.1, 0.95), (0.9, 0.95)]
    
    buffer_h, buffer_v = [], []
    mapa_calibrado = [] 
    h_esq, h_dir, v_cima, v_baixo = 0, 1, 0, 1 
    
    dwell_timer = 0
    TEMPO_FIXACAO = 3.5 

    # --- VARIÁVEIS DO FILTRO UNIFICADO (DEADZONE + LERP) ---
    alvo_x, alvo_y = LARGURA_TELA / 2, ALTURA_TELA / 2
    cursor_x, cursor_y = LARGURA_TELA / 2, ALTURA_TELA / 2
    LIMITE_TREMOR = 18       # Pixels (Deadzone: ignora movimentos menores que isso)
    FATOR_SUAVIZACAO = 0.12  # Lerp: 0.12 = move 12% da distância por frame

    # --- VARIÁVEIS DE MÉTRICAS ---
    latencias = []
    coordenadas_validacao = []
    TEMPO_VALIDACAO = 6.0 

    print("Iniciando... Pressione 'S' para calibrar ou clique no botão Fechar.")

    while cap.isOpened():
        start_time = time.time()
        ret, frame = cap.read()
        if not ret: 
            break
        
        frame = cv2.flip(frame, 1)
        h_f, w_f, _ = frame.shape
        
        if estado == 'INICIO':
            cv2.rectangle(frame, (w_f//2-250, h_f//2-40), (w_f//2+250, h_f//2+40), (0,0,0), -1)
            cv2.putText(frame, "Pressione 'S' para CALIBRAR", (w_f//2-220, h_f//2+10), 1, 1.5, (255,255,255), 2)
            
            if cv2.waitKey(1) & 0xFF == ord('s'): 
                estado = 'CALIBRACAO'

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = detector.detect(mp_image)

        if results.face_landmarks and estado != 'INICIO':
            land = results.face_landmarks[0]
            
            # Cálculo melhorado do Eixo Y (usando o centro geométrico do olho)
            def get_ratios():
                p_iris = np.array([land[473].x, land[473].y])
                p_in = np.array([land[362].x, land[362].y])
                p_out = np.array([land[263].x, land[263].y])
                p_up = np.array([land[386].x, land[386].y])
                p_down = np.array([land[374].x, land[374].y])
                
                rh = np.linalg.norm(p_iris - p_in) / np.linalg.norm(p_out - p_in)
                
                p_center = (p_up + p_down) / 2.0
                dist_vertical_total = np.linalg.norm(p_down - p_up)
                rv = (p_iris[1] - p_center[1]) / dist_vertical_total if dist_vertical_total > 0 else 0
                
                return rh, rv

            cur_h, cur_v = get_ratios()

            if estado == 'CALIBRACAO':
                target = pontos_alvo[ponto_atual]
                tx, ty = int(target[0] * w_f), int(target[1] * h_f)
                
                if dwell_timer == 0: 
                    dwell_timer = time.time()
                decorrido = time.time() - dwell_timer
                
                if decorrido > 0.7: 
                    buffer_h.append(cur_h)
                    buffer_v.append(cur_v)

                cv2.circle(frame, (tx, ty), 35, (255, 255, 255), 2)
                cv2.ellipse(frame, (tx, ty), (35, 35), 0, 0, (decorrido/TEMPO_FIXACAO)*360, (0, 255, 0), 4)
                cv2.putText(frame, f"CALIBRANDO: OLHE PARA O ALVO {ponto_atual+1}/5", (20, 50), 1, 1.5, (0, 255, 255), 2)

                if decorrido >= TEMPO_FIXACAO:
                    mapa_calibrado.append((np.median(buffer_h), np.median(buffer_v)))
                    ponto_atual += 1
                    dwell_timer = 0
                    buffer_h, buffer_v = [], []
                    
                    if ponto_atual >= len(pontos_alvo):
                        # Ancorando as médias baseadas nos pontos que o usuário olhou
                        h_esq = (mapa_calibrado[1][0] + mapa_calibrado[3][0]) / 2.0
                        h_dir = (mapa_calibrado[2][0] + mapa_calibrado[4][0]) / 2.0
                        v_cima = (mapa_calibrado[1][1] + mapa_calibrado[2][1]) / 2.0
                        v_baixo = (mapa_calibrado[3][1] + mapa_calibrado[4][1]) / 2.0
                        
                        estado = 'VALIDACAO' 
                        dwell_timer = 0

            elif estado in ['VALIDACAO', 'LIVRE']:
                # 1. Mapeamento bruto ancorado
                pos_x_bruta = mapear_eixo(cur_h, h_esq, h_dir, w_f * 0.1, w_f * 0.9, 0, w_f)
                pos_y_bruta = mapear_eixo(cur_v, v_cima, v_baixo, h_f * 0.05, h_f * 0.95, 0, h_f)

                # 2. Deadzone (Zona Morta)
                dist_movimento = math.dist((pos_x_bruta, pos_y_bruta), (alvo_x, alvo_y))
                if dist_movimento > LIMITE_TREMOR:
                    alvo_x, alvo_y = pos_x_bruta, pos_y_bruta

                # 3. Suavização Exponencial (Lerp)
                cursor_x += (alvo_x - cursor_x) * FATOR_SUAVIZACAO
                cursor_y += (alvo_y - cursor_y) * FATOR_SUAVIZACAO

                # Desenha o cursor suavizado
                cv2.circle(frame, (int(cursor_x), int(cursor_y)), 12, (0, 255, 0), -1)

                if estado == 'VALIDACAO':
                    tx, ty = int(w_f * 0.5), int(h_f * 0.5)
                    cv2.circle(frame, (tx, ty), 20, (0, 0, 255), -1)
                    
                    if dwell_timer == 0: 
                        dwell_timer = time.time()
                    decorrido = time.time() - dwell_timer

                    cv2.putText(frame, f"VALIDACAO: FIXE NO CENTRO ({int(TEMPO_VALIDACAO - decorrido)}s)", (20, 50), 1, 1.5, (0, 165, 255), 2)

                    if decorrido > 0.5: 
                        coordenadas_validacao.append((cursor_x, cursor_y))
                    
                    if decorrido >= TEMPO_VALIDACAO:
                        erros_euclidianos = [math.dist((cx, cy), (tx, ty)) for cx, cy in coordenadas_validacao]
                        acuracia_media_px = sum(erros_euclidianos) / len(erros_euclidianos)
                        
                        jitter_x = statistics.stdev([c[0] for c in coordenadas_validacao]) if len(coordenadas_validacao) > 1 else 0
                        jitter_y = statistics.stdev([c[1] for c in coordenadas_validacao]) if len(coordenadas_validacao) > 1 else 0
                        
                        latencia_media_ms = (sum(latencias) / len(latencias)) if latencias else 0
                        fps_medio = 1000 / latencia_media_ms if latencia_media_ms > 0 else 0

                        print("\n" + "="*40)
                        print("RESULTADOS DA VALIDAÇÃO")
                        print("="*40)
                        print(f"Erro Médio (Acurácia): {acuracia_media_px:.2f} pixels")
                        print(f"Estabilidade X (Jitter): {jitter_x:.2f} px")
                        print(f"Estabilidade Y (Jitter): {jitter_y:.2f} px")
                        print(f"FPS Médio: {fps_medio:.2f}")
                        print("="*40 + "\n")

                        estado = 'LIVRE'

                elif estado == 'LIVRE':
                    cv2.putText(frame, "LIVRE - Rastreamento Ativo", (20, 50), 1, 1.5, (0, 255, 0), 2)

            # Desenha marcações nos olhos para debug
            for idx, color in [(473, (255,255,255)), (386, (0,0,255)), (374, (0,0,255))]:
                cv2.circle(frame, (int(land[idx].x * w_f), int(land[idx].y * h_f)), 2, color, -1)

        # --- BOTÃO DE FECHAR (DESENHO E LÓGICA) ---
        cv2.rectangle(frame, (w_f - 180, 20), (w_f - 20, 80), (0, 0, 255), -1)
        cv2.putText(frame, "FECHAR (X)", (w_f - 170, 60), 1, 1.0, (255, 255, 255), 2)

        if fechar_app:
            break

        # Cálculo de latência
        end_time = time.time()
        latencia_atual_ms = (end_time - start_time) * 1000
        if estado == 'VALIDACAO':
            latencias.append(latencia_atual_ms)

        cv2.imshow('Sistema de Eye Tracking', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()