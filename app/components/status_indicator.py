from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
import qtawesome as qta


class StatusIndicator(QFrame):
    """
    Pequeno pill flutuante (OS-level) que mostra o estado do rastreamento.

    Estados:
      - "tracking" : verde,  rosto presente e gaze sendo emitido
      - "no_face"  : amarelo, rosto não detectado
      - "offline"  : vermelho, câmera/motor offline
    """

    _STATES = {
        "tracking": ("Rastreando", "#10B981", "fa5s.eye"),
        "no_face":  ("Sem rosto detectado", "#F59E0B", "fa5s.exclamation-triangle"),
        "offline":  ("Câmera offline", "#EF4444", "fa5s.times-circle"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        # OS-level: sempre visível, não rouba foco/cliques
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.setFixedHeight(40)
        self.setMinimumWidth(180)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 16, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background: transparent;")
        self.text_label = QLabel()
        self.text_label.setStyleSheet(
            "background: transparent; color: white; font-size: 13px; font-weight: 600;"
        )

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

        self.set_state("offline")

    def set_state(self, state):
        if state not in self._STATES:
            return
        text, color, icon_name = self._STATES[state]
        self.setStyleSheet(
            f"QFrame {{ background-color: {color}; border-radius: 20px; }}"
        )
        icon = qta.icon(icon_name, color="white")
        self.icon_label.setPixmap(icon.pixmap(18, 18))
        self.text_label.setText(text)
        self.adjustSize()
