

import io
import re
import os
from datetime import datetime
import numpy as np
import cv2
from PIL import Image
import pytesseract
import config
from PyQt5.QtWidgets import QDialog, QMessageBox
from pdf2image import convert_from_path


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
        """Konwersja pierwszej strony PDF do obrazu PIL używając popplera."""
        try:
            # Konwersja PDF do obrazu używając pdf2image (poppler)
            images = convert_from_path(pdf_path, dpi=300)  # Wysoka rozdzielczość
            
            if not images:
                print("PDF nie zawiera stron")
                return None
            
            # Pobieranie pierwszej strony
            first_page = images[0]
            
            # Zapisanie obrazu do debugowania
            debug_path = os.path.join(self.debug_dir, "original_pdf.png")
            first_page.save(debug_path)
            print(f"Zapisano oryginalny obraz do: {debug_path}")
            
            return first_page
            
        except Exception as e:
            print(f"Błąd podczas konwersji PDF do obrazu: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def preprocess_image_for_handwriting(self, image, roi_name="unknown"):
        """Zaawansowane przetwarzanie obrazu dla lepszego rozpoznawania pisma odręcznego."""
        try:
            # Poprzednia implementacja pozostaje bez zmian
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
            configs = [
                (r'--oem 1 --psm 6 -c tessedit_char_whitelist=0123456789.', "Cyfry"),
                (r'--oem 1 --psm 7', "Jedna linia"),
                (r'--oem 1 --psm 7 -c tessedit_char_whitelist=0123456789-', "Cyfry ze znakami")
            ]
            
            for config, config_name in configs:
                text = pytesseract.image_to_string(roi_image, config=config).strip()
                print(f"OCR {roi_name} ({config_name}): '{text}'")
                
                # Zwróć pierwszy niepusty wynik
                if text:
                    return text
            
            print(f"Nie udało się rozpoznać tekstu dla {roi_name}")
            return ""
            
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
            
            # Konwersja PDF do obrazu używając popplera
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
            # Import dialogu lokalnie, aby uniknąć cyklicznych importów
            from views.dialogs.ocr_dialog import OCRResultDialog
            from views.dialogs.manual_dialog import ManualDataEntryDialog
            
            # Próba ekstrakcji danych przy użyciu szablonu
            numer_zlecenia, numer_operatora, data_raportu, debug_info = self.extract_data_from_pdf_with_template(pdf_path)
            
            # Jeśli nie ma informacji debugowania lub dane są niepoprawne
            if not debug_info or numer_zlecenia in ["BŁĄD", "NIEZNANY"]:
                dialog = ManualDataEntryDialog(pdf_path=pdf_path)
                if dialog.exec_() == QDialog.Accepted:
                    manual_data = dialog.get_data()
                    
                    numer_zlecenia = manual_data['numer_zlecenia']
                    numer_operatora = manual_data['numer_operatora']
                    data_raportu = manual_data['data_raportu']
                else:
                    # Użytkownik anulował import
                    return None, None, None
            
            # Jeśli mamy dane debugowania, pokaż dialog podglądu
            elif debug_info:
                dialog = OCRResultDialog(debug_info, pdf_path)
                if dialog.exec_() == QDialog.Accepted:
                    manual_data = dialog.get_data()
                    
                    numer_zlecenia = manual_data['numer_zlecenia']
                    numer_operatora = manual_data['numer_operatora']
                    data_raportu = manual_data['data_raportu']
                    pdf_path = manual_data.get('sciezka_pdf', pdf_path)
                else:
                    # Użytkownik anulował import
                    return None, None, None
            
            # Zwróć dane, nawet jeśli zostały ręcznie poprawione
            return numer_zlecenia, numer_operatora, data_raportu
            
        except Exception as e:
            import traceback
            print(f"Błąd podczas ekstrakji danych z PDF: {e}")
            print(traceback.format_exc())
            return None, None, None

# Dodaj eksport klasy
__all__ = ['PDFProcessor']# -*- coding: utf-8 -*-