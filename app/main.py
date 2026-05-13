import sys
import os
import ctypes # NOVO: Para forçar o ícone na barra de tarefas do Windows

os.environ["QT_API"] = "pyside6"

import qtawesome as qta
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from qfluentwidgets import FluentWindow, NavigationItemPosition, setTheme, Theme, NavigationAvatarWidget
from views.home_view import HomeView

class EyeControlApp(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EyeControl OS")
        setTheme(Theme.LIGHT)

        # --- 1. RESOLVENDO O ÍCONE DA BARRA DE TAREFAS NO WINDOWS ---
        try:
            meu_app_id = "app\\assets\\images\\icone.jpg"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(meu_app_id)
        except ImportError:
            pass # Ignora no Linux/Mac
        
        # --- 2. DEFININDO O ÍCONE ---
        icon_path = os.path.join(os.path.dirname(__file__), 'assets', 'images', 'icone.png')
        
        if os.path.exists(icon_path):
            # Ícone da janela e barra de tarefas
            self.setWindowIcon(QIcon(icon_path))
            
            # --- 3. ÍCONE NO TOPO DO MENU LATERAL ---
            # Adiciona um widget de "Avatar" que o Fluent tem nativo, perfeito para logotipos ou perfil
            self.navigationInterface.addWidget(
                routeKey='profile',
                widget=NavigationAvatarWidget('EyeControl', icon_path),
                onClick=lambda: print('Ir para configurações de perfil'),
                position=NavigationItemPosition.TOP
            )

        # --- CONFIGURAÇÃO DAS TELAS E SIDEBAR ---
        self.home_view = HomeView(self)
        
        self.addSubInterface(
            self.home_view, 
            qta.icon('fa5s.home', color='#111827'), 
            'Home'
        )
        
        self.navigationInterface.addItem(
            routeKey='SpeakInterface',
            icon=qta.icon('fa5s.comment-dots', color='#6B7280'),
            text='Speak',
            position=NavigationItemPosition.TOP
        )
        
        self.navigationInterface.addItem(
            routeKey='AppsInterface',
            icon=qta.icon('fa5s.th', color='#6B7280'),
            text='Apps',
            position=NavigationItemPosition.TOP
        )

        self.navigationInterface.addItem(
            routeKey='SettingsInterface',
            icon=qta.icon('fa5s.cog', color='#6B7280'),
            text='Settings',
            position=NavigationItemPosition.BOTTOM
        )
        
        self.navigationInterface.setExpandWidth(220)
        self.showMaximized()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EyeControlApp()
    sys.exit(app.exec())