import os
import math
import time
import threading

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from scipy.spatial.transform import Rotation as Rscipy

from PySide6.QtCore import QThread, Signal


# ===================== Filtros e utilidades =====================

class OneEuroFilterVector:
    """
    Filtro 1 Euro para vetores 3D. Reduz tremedeira (jitter) sem introduzir
    lag perceptível em movimentos rápidos.
    """
    def __init__(self, t0, x0, min_cutoff=0.00005, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = np.array(x0, dtype=float)
        self.dx_prev = np.zeros_like(self.x_prev)
        self.t_prev = t0

    @staticmethod
    def _smoothing_factor(t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    def __call__(self, t, x):
        x = np.array(x, dtype=float)
        t_e = t - self.t_prev
        if t_e <= 0.0:
            return x

        a_d = self._smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = a_d * dx + (1.0 - a_d) * self.dx_prev

        speed = float(np.linalg.norm(dx_hat))
        cutoff = self.min_cutoff + self.beta * speed
        a = self._smoothing_factor(t_e, cutoff)
        x_hat = a * x + (1.0 - a) * self.x_prev

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t
        return x_hat


def _compute_scale(points_3d):
    n = len(points_3d)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += float(np.linalg.norm(points_3d[i] - points_3d[j]))
            count += 1
    return total / count if count > 0 else 1.0


def _compute_head_pose(face_landmarks, indices, ref_matrix_container, w, h):
    """Pose 3D do crânio via PCA de landmarks do nariz, com estabilização."""
    points_3d = np.array([
        [face_landmarks[i].x * w, face_landmarks[i].y * h, face_landmarks[i].z * w]
        for i in indices
    ])
    center = np.mean(points_3d, axis=0)

    centered = points_3d - center
    cov = np.cov(centered.T)
    _, eigvecs = np.linalg.eigh(cov)
    eigvecs = eigvecs[:, ::-1]  # maior eigenvalue primeiro

    if np.linalg.det(eigvecs) < 0:
        eigvecs[:, 2] *= -1

    r = Rscipy.from_matrix(eigvecs)
    roll, pitch, yaw = r.as_euler('zyx', degrees=False)
    R_final = Rscipy.from_euler('zyx', [roll, pitch, yaw]).as_matrix()

    # Estabiliza sinal dos eixos contra flips do PCA entre frames
    if ref_matrix_container[0] is None:
        ref_matrix_container[0] = R_final.copy()
    else:
        R_ref = ref_matrix_container[0]
        for i in range(3):
            if np.dot(R_final[:, i], R_ref[:, i]) < 0:
                R_final[:, i] *= -1
        ref_matrix_container[0] = R_final.copy()

    return center, R_final, points_3d


def _gaze_to_yaw_pitch(combined_dir):
    """Converte vetor 3D de gaze em (yaw, pitch) em graus, conforme cvml original."""
    reference_forward = np.array([0.0, 0.0, -1.0])
    avg = combined_dir / np.linalg.norm(combined_dir)

    xz = np.array([avg[0], 0.0, avg[2]])
    xz /= np.linalg.norm(xz)
    yaw_rad = math.acos(float(np.clip(np.dot(reference_forward, xz), -1.0, 1.0)))
    if avg[0] < 0:
        yaw_rad = -yaw_rad

    yz = np.array([0.0, avg[1], avg[2]])
    yz /= np.linalg.norm(yz)
    pitch_rad = math.acos(float(np.clip(np.dot(reference_forward, yz), -1.0, 1.0)))
    if avg[1] > 0:
        pitch_rad = -pitch_rad

    yaw_deg = math.degrees(yaw_rad)
    pitch_deg = math.degrees(pitch_rad)

    # Convenção do cvml original: positivo = direita / cima
    if yaw_deg < 0:
        yaw_deg = -yaw_deg
    elif yaw_deg > 0:
        yaw_deg = -yaw_deg

    return yaw_deg, pitch_deg


# ===================== EyeTrackerThread (interface Qt) =====================

# Landmarks do nariz/testa usados para a pose estável
_NOSE_INDICES = [
    10, 151, 9, 8,
    168, 6, 197, 195,
    5, 4, 1,
    133, 362,
]

_LEFT_IRIS_IDX = 468
_RIGHT_IRIS_IDX = 473

# Pontos de calibração no padrão da CalibrationView (centro + 4 cantos)
_CALIB_POINTS = [(0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]


class EyeTrackerThread(QThread):
    """
    Rastreador ocular real (MediaPipe + esfera ocular + 1 Euro).

    Mantém EXATAMENTE a mesma interface de sinais do antigo mock (cvml_mouse),
    para que main.py / CalibrationView funcionem sem alterações.
    """
    motor_pronto = Signal()
    coordenadas_atualizadas = Signal(int, int)
    calibracao_ponto = Signal(int, float)
    fase_validacao = Signal(int)
    calibracao_concluida = Signal()

    TEMPO_POR_PONTO = 1.5     # segundos focado em cada ponto
    TEMPO_VALIDACAO = 3.0     # segundos da fase de validação final

    # Limites default (sobrescritos pela calibração nos cantos)
    DEFAULT_YAW_DEG = 15.0
    DEFAULT_PITCH_DEG = 5.0

    def __init__(self, w_f=1920, h_f=1080, camera_index=0):
        super().__init__()
        self.w_f = w_f
        self.h_f = h_f
        self.camera_index = camera_index

        self.rodando = True

        # ---- Estado de calibração ----
        self.em_calibracao = False
        self.ponto_calib_atual = 0
        self.tempo_inicio_ponto = 0.0
        self._reiniciar_calibracao = False

        # Buffers de amostras (yaw, pitch) por ponto
        self._samples = {i: [] for i in range(len(_CALIB_POINTS))}

        # Offsets e ganhos calculados pela calibração
        self._offset_yaw = 0.0
        self._offset_pitch = 0.0
        self._yaw_degrees = self.DEFAULT_YAW_DEG
        self._pitch_degrees = self.DEFAULT_PITCH_DEG

        # ---- Estado do rastreio das esferas oculares ----
        self._spheres_locked = False
        self._left_offset_local = None
        self._right_offset_local = None
        self._left_calib_scale = None
        self._right_calib_scale = None
        self._base_radius = 20.0

        self._R_ref_nose = [None]
        self._gaze_filter = None

        # Sensibilidade extra ajustável via UI (Settings)
        self._sens_x = 1.0
        self._sens_y = 1.0
        self._sens_lock = threading.Lock()

    # ------------------- API pública (chamada pela UI) -------------------

    def iniciar_calibracao(self):
        """Solicita início (ou reinício) do fluxo de 5 pontos."""
        self._reiniciar_calibracao = True

    def parar(self):
        self.rodando = False
        self.wait()

    def atualizar_sensibilidade(self, sens_x, sens_y):
        with self._sens_lock:
            self._sens_x = float(sens_x)
            self._sens_y = float(sens_y)

    # ------------------- Loop principal -------------------

    def run(self):
        face_landmarker = self._criar_face_landmarker()
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("[EyeTracker] ERRO: não foi possível abrir a câmera.")
            return

        cam_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        cam_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480

        self.motor_pronto.emit()

        try:
            while self.rodando:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue

                if self._reiniciar_calibracao:
                    self._iniciar_calibracao_interna()
                    self._reiniciar_calibracao = False

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                ts_ms = int(time.time() * 1000)
                results = face_landmarker.detect_for_video(mp_image, ts_ms)

                if not results.face_landmarks:
                    continue

                face = results.face_landmarks[0]
                head_center, R_final, nose_pts = _compute_head_pose(
                    face, _NOSE_INDICES, self._R_ref_nose, cam_w, cam_h
                )

                left_iris = face[_LEFT_IRIS_IDX]
                right_iris = face[_RIGHT_IRIS_IDX]
                iris_3d_l = np.array([left_iris.x * cam_w, left_iris.y * cam_h, left_iris.z * cam_w])
                iris_3d_r = np.array([right_iris.x * cam_w, right_iris.y * cam_h, right_iris.z * cam_w])

                if self.em_calibracao:
                    self._passo_calibracao(head_center, R_final, nose_pts, iris_3d_l, iris_3d_r)
                else:
                    if self._spheres_locked:
                        self._emitir_coordenadas(head_center, R_final, nose_pts, iris_3d_l, iris_3d_r)
        finally:
            cap.release()
            try:
                face_landmarker.close()
            except Exception:
                pass

    # ------------------- Calibração -------------------

    def _iniciar_calibracao_interna(self):
        self.em_calibracao = True
        self.ponto_calib_atual = 0
        self.tempo_inicio_ponto = time.time()
        self._samples = {i: [] for i in range(len(_CALIB_POINTS))}
        # Reseta o lock para recalibrar no ponto central
        self._spheres_locked = False
        self._gaze_filter = None
        self._offset_yaw = 0.0
        self._offset_pitch = 0.0
        self._yaw_degrees = self.DEFAULT_YAW_DEG
        self._pitch_degrees = self.DEFAULT_PITCH_DEG

    def _passo_calibracao(self, head_center, R_final, nose_pts, iris_3d_l, iris_3d_r):
        now = time.time()
        elapsed = now - self.tempo_inicio_ponto

        # ---- Ponto 0 (centro): trava as esferas no INÍCIO do foco ----
        if self.ponto_calib_atual == 0 and not self._spheres_locked:
            self._lock_spheres(head_center, R_final, nose_pts, iris_3d_l, iris_3d_r)

        # Se ainda não há esferas, não há gaze: aguarda o lock concluir no frame atual
        if self._spheres_locked and self.ponto_calib_atual < len(_CALIB_POINTS):
            yaw_deg, pitch_deg, _ = self._gaze_atual(head_center, R_final, nose_pts, iris_3d_l, iris_3d_r)
            if yaw_deg is not None:
                # Para os cantos, aplicamos offset central já calibrado
                if self.ponto_calib_atual > 0:
                    yaw_deg += self._offset_yaw
                    pitch_deg += self._offset_pitch
                self._samples[self.ponto_calib_atual].append((yaw_deg, pitch_deg))

        # ---- Calibração dos 5 pontos ----
        if self.ponto_calib_atual < len(_CALIB_POINTS):
            progresso = min(1.0, elapsed / self.TEMPO_POR_PONTO)
            self.calibracao_ponto.emit(self.ponto_calib_atual, progresso)

            if progresso >= 1.0:
                self._consolidar_ponto(self.ponto_calib_atual)
                self.ponto_calib_atual += 1
                self.tempo_inicio_ponto = now

        # ---- Fase de validação ----
        elif self.ponto_calib_atual == len(_CALIB_POINTS):
            restante = max(0, int(self.TEMPO_VALIDACAO - elapsed) + 1)
            self.fase_validacao.emit(restante)
            if elapsed >= self.TEMPO_VALIDACAO:
                self._finalizar_calibracao()

    def _consolidar_ponto(self, idx):
        amostras = self._samples.get(idx, [])
        if not amostras:
            return

        yaws = np.array([a[0] for a in amostras])
        pitches = np.array([a[1] for a in amostras])
        avg_yaw = float(np.median(yaws))
        avg_pitch = float(np.median(pitches))

        if idx == 0:
            # Centro: define offset que zera o gaze
            self._offset_yaw = -avg_yaw
            self._offset_pitch = -avg_pitch
            return

        # Cantos: alvo_x ∈ {0.1, 0.9}, alvo_y ∈ {0.1, 0.9}
        alvo_x, alvo_y = _CALIB_POINTS[idx]
        # Mapeamento usado em _emitir_coordenadas:
        #   screen_x = ((yaw + Y) / (2Y)) * W → yaw_esperado = (2*alvo_x - 1) * Y
        #   screen_y = ((P - pitch) / (2P)) * H → pitch_esperado = (1 - 2*alvo_y) * P
        # → Y_estimado = avg_yaw / (2*alvo_x - 1)
        # → P_estimado = avg_pitch / (1 - 2*alvo_y)
        denom_x = (2 * alvo_x - 1)
        denom_y = (1 - 2 * alvo_y)
        if abs(denom_x) > 1e-3:
            est_yaw_deg = abs(avg_yaw / denom_x)
            # média móvel com defaults para suavizar outliers
            self._yaw_degrees = 0.5 * self._yaw_degrees + 0.5 * est_yaw_deg
        if abs(denom_y) > 1e-3:
            est_pitch_deg = abs(avg_pitch / denom_y)
            self._pitch_degrees = 0.5 * self._pitch_degrees + 0.5 * est_pitch_deg

    def _finalizar_calibracao(self):
        # Sanidade: limita a faixas razoáveis para não estourar a tela
        self._yaw_degrees = float(np.clip(self._yaw_degrees, 5.0, 45.0))
        self._pitch_degrees = float(np.clip(self._pitch_degrees, 3.0, 30.0))
        self.em_calibracao = False
        print(f"[EyeTracker] Calibração concluída: "
              f"offset=({self._offset_yaw:.2f}, {self._offset_pitch:.2f}), "
              f"range=({self._yaw_degrees:.2f}°, {self._pitch_degrees:.2f}°)")
        self.calibracao_concluida.emit()

    # ------------------- Rastreio em modo normal -------------------

    def _emitir_coordenadas(self, head_center, R_final, nose_pts, iris_3d_l, iris_3d_r):
        yaw_deg, pitch_deg, _ = self._gaze_atual(
            head_center, R_final, nose_pts, iris_3d_l, iris_3d_r
        )
        if yaw_deg is None:
            return

        # Aplica offsets de calibração + sensibilidade extra (UI)
        with self._sens_lock:
            sx = self._sens_x
            sy = self._sens_y

        yaw_deg = (yaw_deg + self._offset_yaw) * sx
        pitch_deg = (pitch_deg + self._offset_pitch) * sy

        Y = self._yaw_degrees
        P = self._pitch_degrees

        screen_x = int(((yaw_deg + Y) / (2 * Y)) * self.w_f)
        screen_y = int(((P - pitch_deg) / (2 * P)) * self.h_f)

        screen_x = max(10, min(screen_x, self.w_f - 10))
        screen_y = max(10, min(screen_y, self.h_f - 10))

        self.coordenadas_atualizadas.emit(screen_x, screen_y)

    # ------------------- Helpers do pipeline ocular -------------------

    def _lock_spheres(self, head_center, R_final, nose_pts, iris_3d_l, iris_3d_r):
        nose_scale = _compute_scale(nose_pts)
        camera_dir_world = np.array([0.0, 0.0, 1.0])
        camera_dir_local = R_final.T @ camera_dir_world

        self._left_offset_local = R_final.T @ (iris_3d_l - head_center) + self._base_radius * camera_dir_local
        self._right_offset_local = R_final.T @ (iris_3d_r - head_center) + self._base_radius * camera_dir_local
        self._left_calib_scale = nose_scale
        self._right_calib_scale = nose_scale
        self._spheres_locked = True

    def _gaze_atual(self, head_center, R_final, nose_pts, iris_3d_l, iris_3d_r):
        """Retorna (yaw_deg_raw, pitch_deg_raw, dir_filtrada) no frame atual."""
        if not self._spheres_locked:
            return None, None, None

        nose_scale = _compute_scale(nose_pts)
        scale_l = nose_scale / self._left_calib_scale if self._left_calib_scale else 1.0
        scale_r = nose_scale / self._right_calib_scale if self._right_calib_scale else 1.0

        left_offset = np.asarray(self._left_offset_local, dtype=float)
        right_offset = np.asarray(self._right_offset_local, dtype=float)
        sphere_l = head_center + R_final @ (left_offset * scale_l)
        sphere_r = head_center + R_final @ (right_offset * scale_r)

        left_dir = iris_3d_l - sphere_l
        right_dir = iris_3d_r - sphere_r
        n_l = np.linalg.norm(left_dir)
        n_r = np.linalg.norm(right_dir)
        if n_l < 1e-6 or n_r < 1e-6:
            return None, None, None

        left_dir /= n_l
        right_dir /= n_r
        raw_dir = (left_dir + right_dir) * 0.5
        n = np.linalg.norm(raw_dir)
        if n < 1e-6:
            return None, None, None
        raw_dir /= n

        now = time.time()
        if self._gaze_filter is None:
            self._gaze_filter = OneEuroFilterVector(
                t0=now, x0=raw_dir, min_cutoff=0.00005, beta=5.0
            )
            filtered = raw_dir
        else:
            filtered = self._gaze_filter(now, raw_dir)
            n = np.linalg.norm(filtered)
            if n > 1e-6:
                filtered = filtered / n

        yaw_deg, pitch_deg = _gaze_to_yaw_pitch(filtered)
        return yaw_deg, pitch_deg, filtered

    # ------------------- MediaPipe -------------------

    @staticmethod
    def _criar_face_landmarker():
        model_path = os.path.join(os.path.dirname(__file__), "face_landmarker.task")
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return vision.FaceLandmarker.create_from_options(options)
