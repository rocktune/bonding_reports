#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Dodanie katalogu głównego projektu do ścieżki Pythona
# Aby moduły mogły być importowane prawidłowo
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow


def main():
    """Główna funkcja aplikacji."""
    app = QApplication(sys.argv)
    
    # Ustawienie stylu aplikacji (opcjonalnie)
    # app.setStyle("Fusion")
    
    # Utworzenie i wyświetlenie głównego okna
    window = MainWindow()
    window.show()
    
    # Uruchomienie pętli zdarzeń aplikacji
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()