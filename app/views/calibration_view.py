from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt

class CalibrationView(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #F8F9FA;") 
        self.ponto_atual = 0
        self.progresso = 0.0
        
        self.modo_validacao = False
        self.tempo_validacao = 0

        self.alvos = [(0.5, 0.5), (0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]

    def atualizar_progresso(self, ponto, progresso):
        self.ponto_atual = ponto
        self.progresso = progresso
        self.modo_validacao = False
        self.update() 

    def atualizar_validacao(self, tempo_restante):
        self.modo_validacao = True
        self.tempo_validacao = tempo_restante
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        largura, altura = self.width(), self.height()

        if self.modo_validacao:
            # --- DESENHO DA FASE DE VALIDAÇÃO ---
            tx, ty = int(largura * 0.5), int(altura * 0.5)
            
            painter.setBrush(QColor("#EF4444")) # Vermelho alerta
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(tx - 20, ty - 20, 40, 40)

            painter.setPen(QPen(QColor("#111827"), 2))
            painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
            painter.drawText(tx - 300, ty - 60, 600, 50, Qt.AlignmentFlag.AlignCenter, f"Validação: Fixe no centro ({self.tempo_validacao}s)")
            
        else:
            # --- DESENHO DA FASE DE CALIBRAÇÃO ---
            if self.ponto_atual >= len(self.alvos): return
            tx = int(self.alvos[self.ponto_atual][0] * largura)
            ty = int(self.alvos[self.ponto_atual][1] * altura)

            painter.setBrush(QColor("#4F46E5"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(tx - 15, ty - 15, 30, 30)

            caneta = QPen(QColor("#10B981")) 
            caneta.setWidth(6)
            painter.setPen(caneta)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            angulo_span = int(self.progresso * 360 * 16)
            painter.drawArc(tx - 40, ty - 40, 80, 80, 90 * 16, -angulo_span)