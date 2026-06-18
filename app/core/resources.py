"""
Resolução de caminhos de recursos (assets, modelos) que funciona tanto
rodando como script quanto empacotado pelo PyInstaller.

No executável o PyInstaller extrai os dados para uma pasta temporária
apontada por ``sys._MEIPASS``. Em desenvolvimento, a base é a pasta ``app/``.
"""
import os
import sys


def resource_path(relativo: str) -> str:
    """Retorna o caminho absoluto de um recurso empacotado.

    Use caminhos relativos à pasta ``app/``, por exemplo:
        resource_path("core/face_landmarker.task")
        resource_path("assets/images/icone.ico")
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
    else:
        # Este arquivo está em app/core/ -> sobe um nível para app/
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativo)
