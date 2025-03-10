# -*- coding: utf-8 -*-

import io
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QLineEdit, QDialogButtonBox, QMessageBox, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem)
from PyQt5.QtCore import Qt, QRectF, QPointF, QByteArray  # QByteArray przeniesiony do importu z QtCore
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QBrush  # usunięty QByteArray z QtGui

from controllers.pdf_processor import PDFProcessor


class TemplateCreatorDialog(QDialog):
    """Dialog do tworzenia szablonu rozpoznawania dokumentów."""
    def __init__(self, pdf_path, db_manager, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.db_manager = db_manager
        self.roi = {"numer_zlecenia": None, "numer_operatora": None, "data": None}
        self.current_roi_type = None
        self.selection_start = None
        self.selection_current = None
        self.image = None
        self.pixmap_item = None  # Inicjalizacja atrybutu
        
        self.init_ui()
        self.load_pdf()
        
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika."""
        self.setWindowTitle("Kreator szablonu rozpoznawania")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # Instrukcje
        instructions = QLabel("Zaznacz prostokątne obszary na dokumencie, które zawierają:")
        layout.addWidget(instructions)
        
        # Przyciski wyboru ROI
        roi_buttons_layout = QHBoxLayout()
        
        self.btn_numer_zlecenia = QPushButton("1. Numer zlecenia")
        self.btn_numer_zlecenia.clicked.connect(lambda: self.start_roi_selection("numer_zlecenia"))
        roi_buttons_layout.addWidget(self.btn_numer_zlecenia)
        
        self.btn_numer_operatora = QPushButton("2. Numer operatora")
        self.btn_numer_operatora.clicked.connect(lambda: self.start_roi_selection("numer_operatora"))
        roi_buttons_layout.addWidget(self.btn_numer_operatora)
        
        self.btn_data = QPushButton("3. Data")
        self.btn_data.clicked.connect(lambda: self.start_roi_selection("data"))
        roi_buttons_layout.addWidget(self.btn_data)
        
        layout.addLayout(roi_buttons_layout)
        
        # Obszar podglądu dokumentu
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.NoDrag)
        
        # Obsługa myszy dla zaznaczania obszaru
        self.view.mousePressEvent = self.mouse_press_event
        self.view.mouseMoveEvent = self.mouse_move_event
        self.view.mouseReleaseEvent = self.mouse_release_event
        
        layout.addWidget(self.view)
        
        # Nazwa szablonu
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa szablonu:"))
        self.template_name = QLineEdit("Domyślny szablon")
        name_layout.addWidget(self.template_name)
        layout.addLayout(name_layout)
        
        # Przyciski
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_template)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_pdf(self):
        """Wczytanie pierwszej strony PDF jako obrazu."""
        try:
            # Konwersja PDF do obrazu
            pdf_processor = PDFProcessor(self.db_manager)
            self.image = pdf_processor.pdf_to_pil_image(self.pdf_path)
            
            if self.image:
                # Konwersja obrazu PIL do QPixmap
                img_buffer = io.BytesIO()
                self.image.save(img_buffer, format='PNG')
                img_data = img_buffer.getvalue()
                pixmap = QPixmap()
                pixmap.loadFromData(QByteArray(img_data))
                
                self.pixmap_item = QGraphicsPixmapItem(pixmap)
                self.scene.addItem(self.pixmap_item)
                self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
                
                # Dodanie prostokątów dla już zdefiniowanych ROI
                self.update_roi_rectangles()
            else:
                QMessageBox.critical(self, "Błąd", "Nie można wczytać pliku PDF.")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można wczytać pliku PDF:\n{str(e)}")
    
    def start_roi_selection(self, roi_type):
        """Rozpoczęcie wyboru obszaru zainteresowania (ROI)."""
        self.current_roi_type = roi_type
        
        # Zmiana koloru przycisków
        self.btn_numer_zlecenia.setStyleSheet("")
        self.btn_numer_operatora.setStyleSheet("")
        self.btn_data.setStyleSheet("")
        
        if roi_type == "numer_zlecenia":
            self.btn_numer_zlecenia.setStyleSheet("background-color: #9CF;")
        elif roi_type == "numer_operatora":
            self.btn_numer_operatora.setStyleSheet("background-color: #9CF;")
        elif roi_type == "data":
            self.btn_data.setStyleSheet("background-color: #9CF;")
    
    def mouse_press_event(self, event):
        """Obsługa zdarzenia naciśnięcia przycisku myszy."""
        if self.current_roi_type and self.pixmap_item:
            # Pobierz współrzędne w skali sceny
            scene_pos = self.view.mapToScene(event.pos())
            item_pos = self.pixmap_item.mapFromScene(scene_pos)
            self.selection_start = (item_pos.x(), item_pos.y())
            self.selection_current = self.selection_start
            self.update_roi_rectangles()
        
        # Przekazanie zdarzenia do oryginalnej metody
        QGraphicsView.mousePressEvent(self.view, event)
    
    def mouse_move_event(self, event):
        """Obsługa zdarzenia ruchu myszy."""
        if self.selection_start and self.current_roi_type:
            # Pobierz współrzędne w skali sceny
            scene_pos = self.view.mapToScene(event.pos())
            item_pos = self.pixmap_item.mapFromScene(scene_pos)
            self.selection_current = (item_pos.x(), item_pos.y())
            self.update_roi_rectangles()
        
        # Przekazanie zdarzenia do oryginalnej metody
        QGraphicsView.mouseMoveEvent(self.view, event)
    
    def mouse_release_event(self, event):
        """Obsługa zdarzenia zwolnienia przycisku myszy."""
        if self.selection_start and self.selection_current and self.current_roi_type and self.pixmap_item:
            # Upewnij się, że współrzędne są w granicach obrazu
            x1 = max(0, min(self.selection_start[0], self.pixmap_item.pixmap().width()))
            y1 = max(0, min(self.selection_start[1], self.pixmap_item.pixmap().height()))
            
            scene_pos = self.view.mapToScene(event.pos())
            item_pos = self.pixmap_item.mapFromScene(scene_pos)
            x2 = max(0, min(item_pos.x(), self.pixmap_item.pixmap().width()))
            y2 = max(0, min(item_pos.y(), self.pixmap_item.pixmap().height()))
            
            # Zapewnienie, że x1 < x2 i y1 < y2
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            # Zapisanie ROI
            self.roi[self.current_roi_type] = f"{int(x1)},{int(y1)},{int(x2)},{int(y2)}"
            
            # Reset zaznaczenia
            self.selection_start = None
            self.selection_current = None
            
            # Aktualizacja prostokątów
            self.update_roi_rectangles()
            
            # Zmiana koloru przycisku na zielony, oznaczający zakończony wybór
            if self.current_roi_type == "numer_zlecenia":
                self.btn_numer_zlecenia.setStyleSheet("background-color: #9F9;")
            elif self.current_roi_type == "numer_operatora":
                self.btn_numer_operatora.setStyleSheet("background-color: #9F9;")
            elif self.current_roi_type == "data":
                self.btn_data.setStyleSheet("background-color: #9F9;")
            
            self.current_roi_type = None
        
        # Przekazanie zdarzenia do oryginalnej metody
        QGraphicsView.mouseReleaseEvent(self.view, event)
    
    def update_roi_rectangles(self):
        """Aktualizacja prostokątów reprezentujących obszary zainteresowania."""
        # Usunięcie wszystkich prostokątów
        for item in self.scene.items():
            if isinstance(item, QGraphicsPixmapItem) and item == self.pixmap_item:
                continue
            self.scene.removeItem(item)
        
        # Rysowanie prostokątów dla zapisanych ROI
        colors = {
            "numer_zlecenia": QColor(0, 0, 255, 100),  # Niebieski
            "numer_operatora": QColor(0, 255, 0, 100), # Zielony
            "data": QColor(255, 0, 0, 100)             # Czerwony
        }
        
        for roi_type, roi_data in self.roi.items():
            if roi_data:
                x1, y1, x2, y2 = map(int, roi_data.split(","))
                self.scene.addRect(QRectF(x1, y1, x2-x1, y2-y1), QPen(colors[roi_type]), QBrush(colors[roi_type]))
        
        # Rysowanie aktualnie zaznaczanego obszaru
        if self.selection_start and self.selection_current and self.current_roi_type:
            x1, y1 = self.selection_start
            x2, y2 = self.selection_current
            x1, x2 = min(x1, x2), max(x1, x2)
            y1, y2 = min(y1, y2), max(y1, y2)
            
            self.scene.addRect(
                QRectF(x1, y1, x2-x1, y2-y1),
                QPen(colors[self.current_roi_type]),
                QBrush(colors[self.current_roi_type])
            )
    
    def resizeEvent(self, event):
        """Obsługa zdarzenia zmiany rozmiaru okna."""
        if hasattr(self, 'pixmap_item') and self.pixmap_item:
            self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        super().resizeEvent(event)
    
    def save_template(self):
        """Zapisanie szablonu do bazy danych."""
        # Sprawdzenie, czy wszystkie ROI zostały zdefiniowane
        if not any(self.roi.values()):
            QMessageBox.warning(self, "Niekompletny szablon", 
                              "Nie zdefiniowano żadnego obszaru.\nPrzynajmniej jeden obszar jest wymagany.")
            return
        
        try:
            template_name = self.template_name.text()
            if not template_name:
                template_name = "Domyślny szablon"
            
            self.db_manager.save_template(
                template_name,
                self.roi["numer_zlecenia"],
                self.roi["numer_operatora"],
                self.roi["data"]
            )
            
            QMessageBox.information(self, "Sukces", "Szablon został pomyślnie zapisany.")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać szablonu:\n{str(e)}")