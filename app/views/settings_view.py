from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal
from qfluentwidgets import TitleLabel, SubtitleLabel, BodyLabel, Slider, PushButton
import qtawesome as qta

class SettingsCard(QFrame):
    """ Card reutilizável para cada grupo de configuração """
    def __init__(self, title, description):
        super().__init__()
        self.setStyleSheet("background-color: #F3F4F6; border-radius: 16px;")
        self.setContentsMargins(20, 20, 20, 20)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        
        titulo = SubtitleLabel(title)
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #111827;")
        
        desc = BodyLabel(description)
        desc.setStyleSheet("color: #6B7280; font-size: 14px;")
        desc.setWordWrap(True)
        
        self.layout.addWidget(titulo)
        self.layout.addWidget(desc)

    def add_slider_row(self, label_text, slider, val_label):
        row = QHBoxLayout()
        label = BodyLabel(label_text)
        label.setFixedWidth(150)
        
        row.addWidget(label)
        row.addWidget(slider)
        row.addSpacing(15)
        row.addWidget(val_label)
        self.layout.addLayout(row)


class SettingsView(QWidget):
    # Sinais disparados quando o usuário arrasta os sliders
    voltar_clicado = Signal()
    config_atualizada = Signal(dict) # Envia um dicionário com todos os valores
    recalibrar_clicado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SettingsView")
        
        # --- LAYOUT PRINCIPAL ---
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        main_layout.setContentsMargins(50, 50, 50, 50)
        
        container = QWidget()
        container.setFixedWidth(800) # Limita a largura para ficar elegante
        layout = QVBoxLayout(container)
        layout.setSpacing(30)

        # --- CABEÇALHO ---
        header_layout = QHBoxLayout()
        
        self.btn_voltar = PushButton(qta.icon('fa5s.arrow-left', color='#111827'), "Voltar para Home")
        self.btn_voltar.setFixedWidth(180)
        self.btn_voltar.clicked.connect(self.voltar_clicado.emit)
        
        title = TitleLabel("Configurações do Rastreamento")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #111827;")
        
        header_layout.addWidget(self.btn_voltar)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        # --- 1. CARD: SENSIBILIDADE DO OLHAR ---
        card_sensibilidade = SettingsCard("Sensibilidade de Movimento", "Ajuste o quão rápido o cursor se move em relação ao seu olho.")
        
        # Slider X (Horizontal) - Valores: 50 a 300 (Representa 0.5x a 3.0x)
        self.slider_x = Slider(Qt.Orientation.Horizontal)
        self.slider_x.setRange(50, 300)
        self.slider_x.setValue(130) # Padrão: 1.3x
        self.val_x = BodyLabel("1.3x")
        self.val_x.setFixedWidth(40)
        self.slider_x.valueChanged.connect(lambda v: self.atualizar_label(self.val_x, v / 100.0, "x"))
        card_sensibilidade.add_slider_row("Eixo Horizontal (X):", self.slider_x, self.val_x)

        # Slider Y (Vertical)
        self.slider_y = Slider(Qt.Orientation.Horizontal)
        self.slider_y.setRange(50, 300)
        self.slider_y.setValue(100) # Padrão: 1.0x
        self.val_y = BodyLabel("1.0x")
        self.val_y.setFixedWidth(40)
        self.slider_y.valueChanged.connect(lambda v: self.atualizar_label(self.val_y, v / 100.0, "x"))
        card_sensibilidade.add_slider_row("Eixo Vertical (Y):", self.slider_y, self.val_y)

        # --- 2. CARD: INTERAÇÃO E CLIQUES ---
        card_interacao = SettingsCard("Interação e Gravidade", "Configure o tempo do clique por olhar (Dwell) e o raio do magnetismo.")
        
        # Tempo de Clique - Valores: 5 a 30 (0.5s a 3.0s)
        self.slider_dwell = Slider(Qt.Orientation.Horizontal)
        self.slider_dwell.setRange(5, 30)
        self.slider_dwell.setValue(12) # Padrão: 1.2s
        self.val_dwell = BodyLabel("1.2s")
        self.val_dwell.setFixedWidth(40)
        self.slider_dwell.valueChanged.connect(lambda v: self.atualizar_label(self.val_dwell, v / 10.0, "s"))
        card_interacao.add_slider_row("Tempo de Clique:", self.slider_dwell, self.val_dwell)

        # Gravidade - Valores: 50px a 500px
        self.slider_gravidade = Slider(Qt.Orientation.Horizontal)
        self.slider_gravidade.setRange(50, 500)
        self.slider_gravidade.setValue(180) # Padrão: 180px
        self.val_gravidade = BodyLabel("180px")
        self.val_gravidade.setFixedWidth(50)
        self.slider_gravidade.valueChanged.connect(lambda v: self.atualizar_label(self.val_gravidade, v, "px", int_val=True))
        card_interacao.add_slider_row("Raio Magnético:", self.slider_gravidade, self.val_gravidade)

        # Adiciona os cards na tela
        layout.addWidget(card_sensibilidade)
        layout.addWidget(card_interacao)

        # --- 3. CARD: CALIBRAÇÃO ---
        card_calib = SettingsCard(
            "Calibração",
            "Refaça a calibração de 5 pontos se o cursor estiver impreciso."
        )
        self.btn_recalibrar = PushButton(
            qta.icon('fa5s.expand', color='#FFFFFF'),
            "Recalibrar Rastreamento"
        )
        self.btn_recalibrar.setStyleSheet(
            "QPushButton { background-color: #4F46E5; color: white; border-radius: 10px; "
            "padding: 12px 20px; font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background-color: #4338CA; }"
        )
        self.btn_recalibrar.setFixedHeight(48)
        self.btn_recalibrar.clicked.connect(self.recalibrar_clicado.emit)
        card_calib.layout.addWidget(self.btn_recalibrar)
        layout.addWidget(card_calib)

        main_layout.addWidget(container)

        # Conecta todos os sliders a uma única função de emissão
        self.slider_x.valueChanged.connect(self.emitir_configuracoes)
        self.slider_y.valueChanged.connect(self.emitir_configuracoes)
        self.slider_dwell.valueChanged.connect(self.emitir_configuracoes)
        self.slider_gravidade.valueChanged.connect(self.emitir_configuracoes)

    def atualizar_label(self, label, valor, sufixo, int_val=False):
        if int_val:
            label.setText(f"{int(valor)}{sufixo}")
        else:
            label.setText(f"{valor:.1f}{sufixo}")

    def emitir_configuracoes(self):
        # Empacota tudo num dicionário e manda pra main.py
        configs = {
            "sens_x": self.slider_x.value() / 100.0,
            "sens_y": self.slider_y.value() / 100.0,
            "dwell_time": self.slider_dwell.value() / 10.0,
            "gravidade": int(self.slider_gravidade.value()),
        }
        self.config_atualizada.emit(configs)

    def carregar_configuracoes(self, configs):
        """Aplica valores salvos aos sliders sem disparar config_atualizada repetidamente."""
        if not configs:
            return
        # Bloqueia sinais enquanto seta os valores, depois emite uma única vez
        widgets_bloquear = (self.slider_x, self.slider_y, self.slider_dwell,
                            self.slider_gravidade)
        for w in widgets_bloquear:
            w.blockSignals(True)
        try:
            self.slider_x.setValue(int(configs.get("sens_x", 1.3) * 100))
            self.slider_y.setValue(int(configs.get("sens_y", 1.0) * 100))
            self.slider_dwell.setValue(int(configs.get("dwell_time", 1.2) * 10))
            self.slider_gravidade.setValue(int(configs.get("gravidade", 180)))
            # Atualiza labels
            self.atualizar_label(self.val_x, self.slider_x.value() / 100.0, "x")
            self.atualizar_label(self.val_y, self.slider_y.value() / 100.0, "x")
            self.atualizar_label(self.val_dwell, self.slider_dwell.value() / 10.0, "s")
            self.atualizar_label(self.val_gravidade, self.slider_gravidade.value(), "px", int_val=True)
        finally:
            for w in widgets_bloquear:
                w.blockSignals(False)
        self.emitir_configuracoes()