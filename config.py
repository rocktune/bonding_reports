# -*- coding: utf-8 -*-

import os
import sys
import platform

# Nazwa bazy danych
DB_NAME = "raporty_klejenia.db"

# Konfiguracja ścieżki do Tesseract OCR
if platform.system() == 'Windows':
    TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif platform.system() == 'Linux':
    TESSERACT_PATH = r'/usr/bin/tesseract'
elif platform.system() == 'Darwin':  # macOS
    TESSERACT_PATH = r'/usr/local/bin/tesseract'
else:
    TESSERACT_PATH = 'tesseract'  # Domyślna wartość

# Parametry OCR
OCR_CONFIG_DIGITS = r'--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789.'

# Wymiary i pozycja głównego okna aplikacji
MAIN_WINDOW_GEOMETRY = (100, 100, 1000, 600)  # x, y, szerokość, wysokość