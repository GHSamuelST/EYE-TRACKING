# EyeControl 👁️

Rastreador ocular focado em experiência **UI/UX**, que permite controlar o computador apenas com o movimento dos olhos e da cabeça. O usuário navega pela interface mantendo o olhar sobre uma opção (clique por permanência / *dwell*), podendo abrir aplicativos, rolar páginas, clicar em qualquer ponto da tela e ajustar a sensibilidade do rastreamento.

> Projeto desenvolvido para o TCC do curso de Engenharia Mecatrônica da **Universidade Federal de Catalão**.

---

## 📥 Como instalar

Existem **duas formas** de usar o EyeControl: baixar o executável pronto ou rodar a partir do código-fonte.

### Requisitos

- **Windows 10 ou 11** (64 bits)
- Uma **webcam** funcional
- Boa iluminação no ambiente (o rastreamento depende da câmera enxergar bem o rosto)

### Opção A — Executável pronto (recomendado para usuários)

1. Acesse a aba **[Releases](../../releases)** do repositório.
2. Baixe o arquivo `EyeControl.zip` da versão mais recente.
3. Extraia a pasta `EyeControl` em qualquer lugar do seu computador.
4. Abra a pasta e execute **`EyeControl.exe`**.

> ⚠️ Mantenha todos os arquivos juntos: o `EyeControl.exe` precisa da pasta `_internal` que fica ao lado dele.

### Opção B — A partir do código-fonte (para desenvolvedores)

O projeto usa o gerenciador [**uv**](https://docs.astral.sh/uv/).

```powershell
# 1. Clone o repositório
git clone https://github.com/<seu-usuario>/EYE-TRACKING.git
cd EYE-TRACKING

# 2. Instale as dependências (cria o ambiente virtual automaticamente)
uv sync

# 3. Execute o app
uv run .\app\main.py
```

Se você não usa o `uv`, pode usar `pip` com um ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install pyside6 mediapipe numpy opencv-python pyautogui qtawesome pyside6-fluent-widgets scipy keyboard
python .\app\main.py
```

---

## 🚀 Primeiros passos

1. **Abertura**: ao iniciar, o app exibe uma tela de carregamento enquanto liga a câmera e carrega os modelos de visão computacional.
2. **Onboarding**: na primeira execução, uma tela de boas-vindas explica o funcionamento.
3. **Calibração**: o app pede que você olhe para 5 pontos na tela para mapear o seu olhar. Refaça sempre que sentir imprecisão.
4. **Uso**: mantenha o olhar fixo sobre um card/botão até a barra de progresso completar — isso equivale a um clique.

---

## ✨ Funcionalidades

- **Controle por olhar (dwell click)** — selecione qualquer opção mantendo o foco sobre ela.
- **Atração magnética** — o cursor é "puxado" para o alvo mais próximo, facilitando a seleção.
- **Calibração de 5 pontos** — mapeamento personalizado do olhar, refazível a qualquer momento.
- **Clique em qualquer ponto** — fluxo de mira + confirmação para clicar onde quiser na tela.
- **Menu flutuante (Modo Windows)** — role páginas, volte no navegador, feche apps e volte ao EyeControl sem usar as mãos.
- **Abertura de aplicativos** — abra navegador, arquivos e outros apps pelo olhar.
- **Configurações ajustáveis** — sensibilidade horizontal/vertical, tempo de clique e raio magnético, todos persistentes.
- **Iniciar com o Windows** — opção para abrir o app automaticamente ao ligar o computador (com confirmação).
- **Tutoriais contextuais** — dicas exibidas na primeira vez que você usa cada recurso.

---

## ⚙️ Configurações

Na tela de **Configurações** é possível ajustar:

| Configuração | Descrição |
|---|---|
| **Sensibilidade Horizontal (X)** | Velocidade do cursor no eixo horizontal (0.5x – 3.0x). |
| **Sensibilidade Vertical (Y)** | Velocidade do cursor no eixo vertical (0.5x – 3.0x). |
| **Tempo de Clique** | Quanto tempo de foco é necessário para clicar (0.5s – 3.0s). |
| **Raio Magnético** | Distância de atração do cursor aos alvos (50px – 500px). |
| **Iniciar com o Windows** | Abre o app automaticamente ao ligar o computador. |

As configurações e a calibração são salvas automaticamente e restauradas na próxima abertura.

---

## 📦 Gerar o executável (build)

O projeto inclui o arquivo de configuração [`EyeControl.spec`](EyeControl.spec) do PyInstaller.

```powershell
uv run pyinstaller EyeControl.spec --noconfirm
```

O resultado fica em **`dist\EyeControl\`** (modo *onedir*). Para distribuir, compacte a pasta `EyeControl` inteira em um `.zip` e publique em **Releases** — não versione a pasta `dist/` no Git.

---

## 🗂️ Estrutura do projeto

```
EYE-TRACKING/
├── app/
│   ├── main.py                  # Ponto de entrada e janela principal
│   ├── assets/images/           # Ícones do app (icone.ico / icone.jpg)
│   ├── components/              # Componentes de UI reutilizáveis
│   │   ├── action_card.py       # Cards selecionáveis pelo olhar
│   │   ├── floating_menu.py     # Menu flutuante (Modo Windows)
│   │   ├── nav_card.py
│   │   └── tutorial_overlay.py
│   ├── core/
│   │   ├── cvml.py              # Motor de rastreamento (MediaPipe + OpenCV)
│   │   ├── autostart.py         # Início automático com o Windows
│   │   ├── resources.py         # Resolução de caminhos (dev e .exe)
│   │   └── face_landmarker.task # Modelo de detecção facial
│   ├── styles/                 # Folhas de estilo (QSS)
│   └── views/                  # Telas (home, calibração, apps, etc.)
├── EyeControl.spec             # Configuração de build do PyInstaller
├── pyproject.toml              # Dependências e metadados
└── uv.lock                     # Versões travadas das dependências
```

---

## 🛠️ Tecnologias

- **[PySide6](https://doc.qt.io/qtforpython/)** — interface gráfica (Qt for Python)
- **[PySide6-Fluent-Widgets](https://qfluentwidgets.com/)** — componentes visuais modernos
- **[MediaPipe](https://developers.google.com/mediapipe)** — detecção de pontos faciais (Face Landmarker)
- **[OpenCV](https://opencv.org/)** — captura e processamento de vídeo
- **[NumPy](https://numpy.org/) / [SciPy](https://scipy.org/)** — cálculos vetoriais e de orientação
- **[PyAutoGUI](https://pyautogui.readthedocs.io/)** — controle do mouse e teclado
- **[PyInstaller](https://pyinstaller.org/)** — geração do executável

---

## ❓ Solução de problemas

- **A câmera não liga / tela travada no carregamento**: verifique se nenhum outro programa está usando a webcam e se o app tem permissão de acesso à câmera.
- **O cursor está impreciso**: refaça a calibração em *Configurações → Recalibrar* e melhore a iluminação do ambiente.
- **O cursor se move rápido demais ou devagar**: ajuste as sensibilidades X e Y nas Configurações.
- **O ícone não aparece na barra de tarefas**: rode o `EyeControl.exe` (não rode pelo código se quiser o ícone do executável).

---

## 📄 Licença

Projeto acadêmico desenvolvido como Trabalho de Conclusão de Curso (TCC) — Engenharia Mecatrônica, Universidade Federal de Catalão.
