# -*- coding: utf-8 -*-

import io
import re
import os
from datetime import datetime
import numpy as np
import fitz  # PyMuPDF
import cv2
from PIL import Image
import pytesseract
import config
from PyQt5.QtWidgets import QDialog


class PDFProcessor:
    def __init__(self, db_manager):
        """Inicjalizacja procesora PDF."""
        self.db_manager = db_manager
        
        # Konfiguracja ścieżki do Tesseract OCR
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH
        
        # Tworzymy katalog na obrazy diagnostyczne, jeśli nie istnieje
        self.debug_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug_images")
        os.makedirs(self.debug_dir, exist_ok=True)
        print(f"Katalog debugowania: {self.debug_dir}")
        
    def pdf_to_pil_image(self, pdf_path):
        """Konwersja pierwszej strony PDF do obrazu PIL bez użycia popplera."""
        try:
            # Otwarcie PDF za pomocą PyMuPDF (fitz)
            doc = fitz.open(pdf_path)
            if doc.page_count == 0:
                print("PDF nie zawiera stron")
                return None
            
            # Pobieranie pierwszej strony
            page = doc[0]
            
            # Renderowanie strony z większą rozdzielczością (zoom 4x)
            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4))  # Zwiększona rozdzielczość dla lepszego rozpoznawania
            
            # Konwersja do obrazu PIL
            img_data = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_data))
            
            # Zapisanie obrazu do debugowania
            debug_path = os.path.join(self.debug_dir, "original_pdf.png")
            pil_img.save(debug_path)
            print(f"Zapisano oryginalny obraz do: {debug_path}")
            
            return pil_img
            
        except Exception as e:
            print(f"Błąd podczas konwersji PDF do obrazu: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def preprocess_image_for_handwriting(self, image, roi_name="unknown"):
        """Zaawansowane przetwarzanie obrazu dla lepszego rozpoznawania pisma odręcznego."""
        try:
            # Zapisanie oryginalnego obrazu ROI do debugowania
            debug_path = os.path.join(self.debug_dir, f"roi_{roi_name}_original.png")
            image.save(debug_path)
            print(f"Zapisano oryginalny ROI do: {debug_path}")
            
            # Konwersja PIL Image do tablicy numpy
            np_image = np.array(image)
            
            # Konwersja do skali szarości
            if len(np_image.shape) == 3:
                gray = cv2.cvtColor(np_image, cv2.COLOR_RGB2GRAY)
            else:
                gray = np_image
            
            # Zapisanie obrazu w skali szarości do debugowania
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_gray.png"), gray)
            
            # Eksperymentujemy z różnymi metodami przetwarzania obrazu
            
            # 1. Metoda: Binaryzacja adaptacyjna
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_binary_adaptive.png"), binary)
            
            # 2. Metoda: Prosta binaryzacja z progiem Otsu
            _, binary_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_binary_otsu.png"), binary_otsu)
            
            # 3. Metoda: Zastosowanie filtru rozmycia, a następnie binaryzacja
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary_blur = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_binary_blur.png"), binary_blur)
            
            # Wybór metody binaryzacji (możemy przełączać między metodami)
            # binary = binary_adaptive
            binary = binary_otsu
            
            # Usuwanie szumu
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_opening.png"), opening)
            
            # Dylatacja tekstu (pogrubienie) - pomaga połączyć przerwane linie w piśmie odręcznym
            dilated = cv2.dilate(opening, np.ones((2, 2), np.uint8), iterations=1)
            cv2.imwrite(os.path.join(self.debug_dir, f"roi_{roi_name}_dilated.png"), dilated)
            
            # Konwersja z powrotem do PIL Image
            processed_image = Image.fromarray(dilated)
            
            # Zapisanie końcowego przetworzonego obrazu
            debug_path = os.path.join(self.debug_dir, f"roi_{roi_name}_processed.png")
            processed_image.save(debug_path)
            print(f"Zapisano przetworzony ROI do: {debug_path}")
            
            return processed_image
        except Exception as e:
            print(f"Błąd podczas przetwarzania obrazu: {e}")
            import traceback
            traceback.print_exc()
            return image  # Zwróć oryginalny obraz w przypadku błędu
    
    def extract_text_from_roi(self, image, roi_data, roi_name="unknown"):
        """Ekstrakcja tekstu z określonego obszaru zainteresowania (ROI)."""
        if not roi_data:
            print(f"Brak danych ROI dla {roi_name}")
            return ""
        
        try:
            # Parsowanie danych ROI
            roi = [int(val) for val in roi_data.split(',')]
            if len(roi) != 4:
                print(f"Nieprawidłowe dane ROI dla {roi_name}: {roi_data}")
                return ""
            
            print(f"Wycinanie ROI {roi_name} z koordynatami: {roi}")
            
            # Wycięcie obszaru zainteresowania
            roi_image = image.crop((roi[0], roi[1], roi[2], roi[3]))
            
            # Przetworzenie obrazu dla lepszego OCR
            roi_image = self.preprocess_image_for_handwriting(roi_image, roi_name)
            
            # Spróbujmy różnych konfiguracji OCR
            
            # 1. Domyślna konfiguracja - tylko cyfry i kropki
            digits_config = r'--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789.'
            text_digits = pytesseract.image_to_string(roi_image, config=digits_config).strip()
            print(f"OCR {roi_name} (tylko cyfry): '{text_digits}'")
            
            # 2. Konfiguracja dla jednej linii tekstu
            line_config = r'--oem 1 --psm 7'
            text_line = pytesseract.image_to_string(roi_image, config=line_config).strip()
            print(f"OCR {roi_name} (jedna linia): '{text_line}'")
            
            # 3. Konfiguracja dla liczb
            digits_config2 = r'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789-.'
            text_digits2 = pytesseract.image_to_string(roi_image, config=digits_config2).strip()
            print(f"OCR {roi_name} (tylko cyfry i znaki specjalne): '{text_digits2}'")
            
            # 4. Szybka konfiguracja - mniej dokładna, ale szybsza
            fast_config = r'--oem 0 --psm 6'
            text_fast = pytesseract.image_to_string(roi_image, config=fast_config).strip()
            print(f"OCR {roi_name} (szybki tryb): '{text_fast}'")
            
            # Wybór metody OCR (możemy przełączać między metodami)
            if any(c.isdigit() for c in text_digits2):
                text = text_digits2
            elif any(c.isdigit() for c in text_digits):
                text = text_digits
            elif any(c.isdigit() for c in text_line):
                text = text_line
            else:
                text = text_fast
            
            print(f"Wybrany wynik OCR dla {roi_name}: '{text}'")
            
            return text
        except Exception as e:
            print(f"Błąd podczas ekstrakcji tekstu z ROI {roi_name}: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def format_to_pattern(self, digits):
        """Formatowanie ciągu cyfr do wzoru XXX-XXXX-XXXX-XXX."""
        # Usunięcie wszystkich nie-cyfr
        clean_digits = re.sub(r'[^0-9]', '', digits)
        print(f"Cyfry po oczyszczeniu: '{clean_digits}'")
        
        # Sprawdzenie, czy mamy wystarczającą liczbę cyfr
        if len(clean_digits) >= 15:
            # Formatowanie do wzoru XXX-XXXX-XXXX-XXX
            result = f"{clean_digits[0:3]}-{clean_digits[3:7]}-{clean_digits[7:11]}-{clean_digits[11:14]}"
            print(f"Sformatowany numer zlecenia: {result}")
            return result
        elif len(clean_digits) > 0:
            # Uzupełnienie zerami, jeśli brakuje cyfr
            padded_digits = clean_digits.ljust(15, '0')
            result = f"{padded_digits[0:3]}-{padded_digits[3:7]}-{padded_digits[7:11]}-{padded_digits[11:14]}"
            print(f"Uzupełniony numer zlecenia: {result}")
            return result
        else:
            print("Nie znaleziono cyfr - używam 'NIEZNANY'")
            return "NIEZNANY"
    
    def format_date(self, date_text):
        """Formatowanie daty do formatu dd.mm.yyyy."""
        print(f"Formatowanie daty z tekstu: '{date_text}'")
        
        # Usunięcie wszystkich nie-cyfr (z wyjątkiem kropek i myślników)
        clean_date = re.sub(r'[^0-9.-]', '', date_text)
        print(f"Oczyszczony tekst daty: '{clean_date}'")
        
        # Najpierw sprawdź, czy data już jest w formacie dd.mm.yyyy lub dd.mm.yy
        dot_pattern = r'(\d{1,2})\.(\d{1,2})\.(\d{2,4})'
        dash_pattern = r'(\d{1,2})-(\d{1,2})-(\d{2,4})'
        
        dot_match = re.match(dot_pattern, clean_date)
        dash_match = re.match(dash_pattern, clean_date)
        
        if dot_match:
            day, month, year = dot_match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            
            # Jeśli rok ma 2 cyfry, dodaj "20" przed nim
            if len(year) == 2:
                year = "20" + year
                
            result = f"{day}.{month}.{year}"
            print(f"Dopasowano format z kropkami: {result}")
            return result
            
        elif dash_match:
            day, month, year = dash_match.groups()
            day = day.zfill(2)
            month = month.zfill(2)
            
            # Jeśli rok ma 2 cyfry, dodaj "20" przed nim
            if len(year) == 2:
                year = "20" + year
                
            result = f"{day}.{month}.{year}"
            print(f"Dopasowano format z myślnikami: {result}")
            return result
        
        # Jeśli nie pasuje do wzorców, spróbuj odczytać same cyfry
        digits = re.findall(r'\d', clean_date)
        print(f"Znalezione cyfry: {digits}")
        
        if len(digits) >= 4:  # co najmniej dzień i miesiąc
            day = ''.join(digits[0:2]).zfill(2)
            month = ''.join(digits[2:4]).zfill(2)
            
            if len(digits) >= 8:
                year = ''.join(digits[4:8])
            elif len(digits) >= 6:
                year = "20" + ''.join(digits[4:6])
            else:
                year = datetime.now().strftime("%Y")
                
            result = f"{day}.{month}.{year}"
            print(f"Sformatowana data z cyfr: {result}")
            return result
        
        print(f"Nie udało się sformatować daty - używam oryginalnego tekstu lub 'NIEZNANA'")
        return clean_date if clean_date else "NIEZNANA"
    
    def extract_data_from_pdf_with_template(self, pdf_path):
        """Ekstrakcja danych z PDF przy użyciu szablonu."""
        try:
            # Pobranie szablonu
            template = self.db_manager.get_template()
            if not template:
                print("Brak szablonu rozpoznawania")
                return "NIEZNANY", "NIEZNANY", "NIEZNANA", None
            
            print(f"Szablon rozpoznawania: ID={template[0]}, Nazwa={template[1]}")
            print(f"ROI dla numeru zlecenia: {template[2]}")
            print(f"ROI dla numeru operatora: {template[3]}")
            print(f"ROI dla daty: {template[4]}")
            
            # Konwersja PDF do obrazu używając PyMuPDF
            image = self.pdf_to_pil_image(pdf_path)
            if not image:
                print("Nie udało się skonwertować PDF do obrazu")
                return "NIEZNANY", "NIEZNANY", "NIEZNANA", None
            
            # Ekstrakcja tekstu z poszczególnych ROI
            numer_zlecenia_raw = self.extract_text_from_roi(image, template[2], "numer_zlecenia")  # roi_numer_zlecenia
            numer_operatora_raw = self.extract_text_from_roi(image, template[3], "numer_operatora")  # roi_numer_operatora
            data_raportu_raw = self.extract_text_from_roi(image, template[4], "data")    # roi_data
            
            # Formatowanie numeru zlecenia według wzoru XXX-XXXX-XXXX-XXX
            numer_zlecenia = self.format_to_pattern(numer_zlecenia_raw)
            
            # Formatowanie numeru operatora (tylko cyfry)
            numer_operatora = re.sub(r'[^0-9]', '', numer_operatora_raw)
            if not numer_operatora:
                numer_operatora = "NIEZNANY"
            
            # Formatowanie daty do dd.mm.yyyy
            data_raportu = self.format_date(data_raportu_raw)
            
            # Zapisanie obrazu do debugowania
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            # Słownik z informacjami diagnostycznymi
            debug_info = {
                'image_data': img_data,
                'template': template,
                'numer_zlecenia': numer_zlecenia,
                'numer_operatora': numer_operatora,
                'data_raportu': data_raportu,
                'numer_zlecenia_raw': numer_zlecenia_raw,
                'numer_operatora_raw': numer_operatora_raw,
                'data_raportu_raw': data_raportu_raw
            }
            
            print("Wykryte dane:")
            print(f"Numer zlecenia: {numer_zlecenia} (surowy: {numer_zlecenia_raw})")
            print(f"Numer operatora: {numer_operatora} (surowy: {numer_operatora_raw})")
            print(f"Data: {data_raportu} (surowy: {data_raportu_raw})")
            
            return numer_zlecenia, numer_operatora, data_raportu, debug_info
            
        except Exception as e:
            print(f"Błąd podczas przetwarzania PDF: {e}")
            import traceback
            traceback.print_exc()
            return "BŁĄD", "BŁĄD", "BŁĄD", None
    
    def extract_data_from_pdf(self, pdf_path):
        """Główna funkcja ekstrakcji danych z PDF."""
        try:
            # ZMIANA: Najpierw definiujemy klasy dialogów zamiast ich importowania
            # Dzięki temu unikamy cyklicznych importów
            
            # Definicja klasy OCRResultDialog
            class OCRResultDialog(QDialog):
                def __init__(self, debug_info, pdf_path, parent=None):
                    super().__init__(parent)
                    self.debug_info = debug_info
                    self.pdf_path = pdf_path
                    
                    # Import widgetów i modułów potrzebnych dla dialogu
                    from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                                                QLineEdit, QTabWidget, QWidget, QFormLayout, 
                                                QDialogButtonBox, QFileDialog, QTextEdit, QScrollArea)
                    from PyQt5.QtCore import Qt, QByteArray
                    from PyQt5.QtGui import QPixmap
                    
                    # Inicjalizacja UI
                    self.setWindowTitle("Podgląd i edycja danych")
                    self.setMinimumSize(800, 600)
                    
                    layout = QVBoxLayout()
                    
                    # Zakładki
                    self.tab_widget = QTabWidget()
                    self.tab_preview = QWidget()
                    self.tab_manual = QWidget()
                    self.tab_debug = QWidget()
                    
                    self.tab_widget.addTab(self.tab_preview, "Podgląd dokumentu")
                    self.tab_widget.addTab(self.tab_manual, "Edycja danych")
                    self.tab_widget.addTab(self.tab_debug, "Informacje diagnostyczne")
                    
                    # Zakładka podglądu
                    preview_layout = QVBoxLayout()
                    
                    # Podgląd dokumentu z zaznaczonymi obszarami
                    preview_layout.addWidget(QLabel("<b>Dokument z zaznaczonymi obszarami:</b>"))
                    
                    self.image_view = QLabel()
                    self.image_view.setAlignment(Qt.AlignCenter)
                    
                    # Wczytanie obrazu
                    pixmap = QPixmap()
                    pixmap.loadFromData(QByteArray(self.debug_info['image_data']))
                    
                    # Skalowanie obrazu, jeśli jest zbyt duży
                    max_width = 700
                    if pixmap.width() > max_width:
                        pixmap = pixmap.scaledToWidth(max_width, Qt.SmoothTransformation)
                    
                    self.image_view.setPixmap(pixmap)
                    
                    scroll_area = QScrollArea()
                    scroll_area.setWidget(self.image_view)
                    scroll_area.setWidgetResizable(True)
                    preview_layout.addWidget(scroll_area)
                    
                    # Rozpoznane dane
                    preview_layout.addWidget(QLabel("<b>Rozpoznane dane:</b>"))
                    data_form = QFormLayout()
                    
                    self.found_zlecenie = QLineEdit(self.debug_info['numer_zlecenia'])
                    self.found_zlecenie.setReadOnly(True)
                    
                    self.found_operator = QLineEdit(self.debug_info['numer_operatora'])
                    self.found_operator.setReadOnly(True)
                    
                    self.found_data = QLineEdit(self.debug_info['data_raportu'])
                    self.found_data.setReadOnly(True)
                    
                    data_form.addRow("Rozpoznany numer zlecenia:", self.found_zlecenie)
                    data_form.addRow("Rozpoznany numer operatora:", self.found_operator)
                    data_form.addRow("Rozpoznana data:", self.found_data)
                    
                    preview_layout.addLayout(data_form)
                    
                    self.tab_preview.setLayout(preview_layout)
                    
                    # Zakładka edycji danych
                    manual_layout = QVBoxLayout()
                    manual_layout.addWidget(QLabel("Zweryfikuj rozpoznane dane lub wprowadź je ręcznie:"))
                    
                    form_layout = QFormLayout()
                    
                    self.numer_zlecenia_edit = QLineEdit()
                    self.numer_zlecenia_edit.setPlaceholderText("Format: XXX-XXXX-XXXX-XXX")
                    
                    self.numer_operatora_edit = QLineEdit()
                    self.data_raportu_edit = QLineEdit()
                    self.data_raportu_edit.setPlaceholderText("Format: DD.MM.YYYY")
                    
                    form_layout.addRow("Numer zlecenia:", self.numer_zlecenia_edit)
                    form_layout.addRow("Numer operatora:", self.numer_operatora_edit)
                    form_layout.addRow("Data raportu:", self.data_raportu_edit)
                    
                    # Dodanie pola edycji ścieżki do pliku PDF
                    self.sciezka_pdf_edit = QLineEdit(self.pdf_path)
                    self.sciezka_pdf_edit.setReadOnly(True)
                    
                    browse_btn = QPushButton("Zmień...")
                    browse_btn.clicked.connect(self.browse_pdf)
                    
                    path_layout = QHBoxLayout()
                    path_layout.addWidget(self.sciezka_pdf_edit)
                    path_layout.addWidget(browse_btn)
                    
                    form_layout.addRow("Ścieżka do pliku PDF:", path_layout)
                    
                    manual_layout.addLayout(form_layout)
                    
                    # Wypełnienie wartościami, jeśli zostały rozpoznane
                    if self.debug_info['numer_zlecenia'] != "NIEZNANY":
                        self.numer_zlecenia_edit.setText(self.debug_info['numer_zlecenia'])
                    
                    if self.debug_info['numer_operatora'] != "NIEZNANY":
                        self.numer_operatora_edit.setText(self.debug_info['numer_operatora'])
                    
                    if self.debug_info['data_raportu'] != "NIEZNANA":
                        self.data_raportu_edit.setText(self.debug_info['data_raportu'])
                        
                    self.tab_manual.setLayout(manual_layout)
                    
                    # Zakładka informacji diagnostycznych
                    debug_layout = QVBoxLayout()
                    debug_layout.addWidget(QLabel("<b>Informacje diagnostyczne:</b>"))
                    
                    debug_text = QTextEdit()
                    debug_text.setReadOnly(True)
                    
                    debug_info_str = f"Surowe dane rozpoznane z OCR:\n\n"
                    debug_info_str += f"Numer zlecenia (surowy): {self.debug_info.get('numer_zlecenia_raw', 'brak')}\n"
                    debug_info_str += f"Numer operatora (surowy): {self.debug_info.get('numer_operatora_raw', 'brak')}\n"
                    debug_info_str += f"Data (surowa): {self.debug_info.get('data_raportu_raw', 'brak')}\n\n"
                    
                    debug_info_str += "Szablon rozpoznawania:\n"
                    template = self.debug_info.get('template')
                    if template:
                        debug_info_str += f"ID szablonu: {template[0]}\n"
                        debug_info_str += f"Nazwa szablonu: {template[1]}\n"
                        debug_info_str += f"ROI numer zlecenia: {template[2]}\n"
                        debug_info_str += f"ROI numer operatora: {template[3]}\n"
                        debug_info_str += f"ROI data: {template[4]}\n"
                    else:
                        debug_info_str += "Brak szablonu rozpoznawania\n"
                        
                    debug_text.setText(debug_info_str)
                    debug_layout.addWidget(debug_text)
                    
                    self.tab_debug.setLayout(debug_layout)
                    
                    # Dodanie zakładek do głównego układu
                    layout.addWidget(self.tab_widget)
                    
                    # Przyciski
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    button_box.accepted.connect(self.accept)
                    button_box.rejected.connect(self.reject)
                    layout.addWidget(button_box)
                    
                    self.setLayout(layout)
                    
                    # Przejdź od razu do zakładki edycji danych
                    self.tab_widget.setCurrentIndex(1)
                
                def browse_pdf(self):
                    """Wybór nowej ścieżki do pliku PDF."""
                    from PyQt5.QtWidgets import QFileDialog
                    
                    file_path, _ = QFileDialog.getOpenFileName(
                        self, "Wybierz plik PDF", "", "Pliki PDF (*.pdf)"
                    )
                    
                    if file_path:
                        self.sciezka_pdf_edit.setText(file_path)
                
                def get_data(self):
                    """Zwraca wprowadzone dane."""
                    return {
                        'numer_zlecenia': self.numer_zlecenia_edit.text(),
                        'numer_operatora': self.numer_operatora_edit.text(),
                        'data_raportu': self.data_raportu_edit.text(),
                        'sciezka_pdf': self.sciezka_pdf_edit.text()
                    }
            
            # Definicja klasy ManualDataEntryDialog
            class ManualDataEntryDialog(QDialog):
                def __init__(self, parent=None, pdf_path=None):
                    super().__init__(parent)
                    self.pdf_path = pdf_path
                    
                    # Import widgetów potrzebnych dla dialogu
                    from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                                                QLineEdit, QFormLayout, QDialogButtonBox, QFileDialog)
                    
                    self.setWindowTitle("Wprowadź dane raportu")
                    self.setMinimumWidth(400)
                    
                    layout = QVBoxLayout()
                    
                    # Komunikat
                    layout.addWidget(QLabel("Wprowadź dane raportu ręcznie:"))
                    
                    # Formularz
                    form_layout = QFormLayout()
                    
                    self.numer_zlecenia_edit = QLineEdit()
                    self.numer_zlecenia_edit.setPlaceholderText("Format: XXX-XXXX-XXXX-XXX")
                    
                    self.numer_operatora_edit = QLineEdit()
                    self.data_raportu_edit = QLineEdit()
                    self.data_raportu_edit.setPlaceholderText("Format: DD.MM.YYYY")
                    
                    form_layout.addRow("Numer zlecenia:", self.numer_zlecenia_edit)
                    form_layout.addRow("Numer operatora:", self.numer_operatora_edit)
                    form_layout.addRow("Data raportu:", self.data_raportu_edit)
                    
                    # Dodanie pola edycji ścieżki do pliku PDF
                    if self.pdf_path:
                        self.sciezka_pdf_edit = QLineEdit(self.pdf_path)
                        self.sciezka_pdf_edit.setReadOnly(True)
                        
                        browse_btn = QPushButton("Zmień...")
                        browse_btn.clicked.connect(self.browse_pdf)
                        
                        path_layout = QHBoxLayout()
                        path_layout.addWidget(self.sciezka_pdf_edit)
                        path_layout.addWidget(browse_btn)
                        
                        form_layout.addRow("Ścieżka do pliku PDF:", path_layout)
                    
                    layout.addLayout(form_layout)
                    
                    # Przyciski
                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                    button_box.accepted.connect(self.accept)
                    button_box.rejected.connect(self.reject)
                    layout.addWidget(button_box)
                    
                    self.setLayout(layout)
                
                def browse_pdf(self):
                    """Wybór nowej ścieżki do pliku PDF."""
                    from PyQt5.QtWidgets import QFileDialog
                    
                    file_path, _ = QFileDialog.getOpenFileName(
                        self, "Wybierz plik PDF", "", "Pliki PDF (*.pdf)"
                    )
                    
                    if file_path:
                        self.sciezka_pdf_edit.setText(file_path)
                
                def get_data(self):
                    """Zwraca wprowadzone dane."""
                    data = {
                        'numer_zlecenia': self.numer_zlecenia_edit.text(),
                        'numer_operatora': self.numer_operatora_edit.text(),
                        'data_raportu': self.data_raportu_edit.text()
                    }
                    
                    if hasattr(self, 'sciezka_pdf_edit'):
                        data['sciezka_pdf'] = self.sciezka_pdf_edit.text()
                        
                    return data
            
            # Próba ekstrakcji danych przy użyciu szablonu
            numer_zlecenia, numer_operatora, data_raportu, debug_info = self.extract_data_from_pdf_with_template(pdf_path)
            
            # Zawsze pokazuj dialog podglądu i edycji, nawet jeśli dane zostały poprawnie rozpoznane
            if debug_info:
                dialog = OCRResultDialog(debug_info, pdf_path)
                if dialog.exec_() == QDialog.Accepted:
                    manual_data = dialog.get_data()
                    
                    numer_zlecenia = manual_data['numer_zlecenia']
                    numer_operatora = manual_data['numer_operatora'] 
                    data_raportu = manual_data['data_raportu']
            else:
                # Jeśli nie ma informacji debugowania, wyświetl prosty dialog
                dialog = ManualDataEntryDialog(pdf_path=pdf_path)
                if dialog.exec_() == QDialog.Accepted:
                    manual_data = dialog.get_data()
                    
                    numer_zlecenia = manual_data['numer_zlecenia']
                    numer_operatora = manual_data['numer_operatora']
                    data_raportu = manual_data['data_raportu']
                else:
                    # Użytkownik anulował import
                    return None, None, None
            
            return numer_zlecenia, numer_operatora, data_raportu
            
        except Exception as e:
            import traceback
            print(f"Błąd podczas ekstrakji danych z PDF: {e}")
            print(traceback.format_exc())
            return "BŁĄD", "BŁĄD", "BŁĄD"