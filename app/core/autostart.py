"""
Gerencia o início automático do app junto com o Windows.

Usa a chave de Registro "Run" do usuário atual
(HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run),
que não exige privilégios de administrador.

Funciona em dois cenários:
  - Rodando como script Python (durante o desenvolvimento): registra o
    interpretador (pythonw.exe) + caminho do main.py.
  - Rodando como executável congelado (PyInstaller / sys.frozen): registra
    o caminho do próprio .exe.
"""
import os
import sys

# winreg só existe no Windows
try:
    import winreg
except ImportError:  # pragma: no cover - ambientes não-Windows
    winreg = None

APP_NAME = "EyeControl"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _comando_de_inicializacao() -> str:
    """Monta a linha de comando que o Windows deve executar ao iniciar."""
    if getattr(sys, "frozen", False):
        # Executável gerado pelo PyInstaller: aponta para o próprio .exe
        return f'"{sys.executable}"'

    # Modo desenvolvimento: usa pythonw.exe (sem console) + main.py
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    interpretador = pythonw if os.path.exists(pythonw) else sys.executable
    return f'"{interpretador}" "{script}"'


def esta_ativado() -> bool:
    """Retorna True se o app está registrado para iniciar com o Windows."""
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as chave:
            valor, _ = winreg.QueryValueEx(chave, APP_NAME)
            return bool(valor)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def ativar() -> bool:
    """Registra o app para iniciar com o Windows. Retorna True em caso de sucesso."""
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as chave:
            winreg.SetValueEx(chave, APP_NAME, 0, winreg.REG_SZ, _comando_de_inicializacao())
        return True
    except OSError as e:
        print(f"[Autostart] Falha ao ativar: {e}")
        return False


def desativar() -> bool:
    """Remove o app da inicialização do Windows. Retorna True em caso de sucesso."""
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as chave:
            winreg.DeleteValue(chave, APP_NAME)
        return True
    except FileNotFoundError:
        return True  # Já não estava registrado
    except OSError as e:
        print(f"[Autostart] Falha ao desativar: {e}")
        return False


def definir(ativado: bool) -> bool:
    """Ativa ou desativa o início automático conforme o booleano."""
    return ativar() if ativado else desativar()
