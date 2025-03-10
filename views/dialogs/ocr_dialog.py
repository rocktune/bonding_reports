# -*- coding: utf-8 -*-

import io
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QLineEdit, QDialogButtonBox, QMessageBox, QGraphicsView, 
                            QGraphicsScene, QGraphicsPixmapItem, QWidget, 
                            QFormLayout, QScrollArea)
from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QPixmap


class OCRResultDialog(QDialog):
    def __init__(self, debug_info, pdf_path, parent=None):
        super().__init__(parent)
        self.debug_info = debug_info
        self.pdf_path = pdf_path
        
        self.setWindowTitle("Import dokumentu")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Lewa strona - podgląd dokumentu
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
        
        # Formularz edycji danych
        form_layout = QFormLayout()
        
        # Pola edycji danych
        self.numer_zlecenia_edit = QLineEdit()
        self.numer_zlecenia_edit.setPlaceholderText("Format: XXX-XXXX-XXXX-XXX")
        
        self.numer_operatora_edit = QLineEdit()
        self.data_raportu_edit = QLineEdit()
        self.data_raportu_edit.setPlaceholderText("Format: DD.MM.YYYY")
        
        # Ścieżka do pliku PDF
        self.sciezka_pdf_edit = QLineEdit(self.pdf_path)
        self.sciezka_pdf_edit.setReadOnly(True)
        
        browse_btn = QPushButton("Zmień...")
        browse_btn.clicked.connect(self.browse_pdf)
        
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(self.sciezka_pdf_edit)
        pdf_layout.addWidget(browse_btn)
        
        # Dodanie etykiet opisowych dla rozpoznanych danych
        form_layout.addRow("Rozpoznany numer zlecenia:", self.create_readonly_field(self.debug_info['numer_zlecenia']))
        form_layout.addRow("Numer zlecenia:", self.numer_zlecenia_edit)
        
        form_layout.addRow("Rozpoznany numer operatora:", self.create_readonly_field(self.debug_info['numer_operatora']))
        form_layout.addRow("Numer operatora:", self.numer_operatora_edit)
        
        form_layout.addRow("Rozpoznana data:", self.create_readonly_field(self.debug_info['data_raportu']))
        form_layout.addRow("Data raportu:", self.data_raportu_edit)
        
        form_layout.addRow("Ścieżka do pliku PDF:", pdf_layout)
        
        # Dodanie formularza do głównego układu
        preview_layout.addLayout(form_layout)
        
        # Przycisk kopiowania rozpoznanych danych
        kopiuj_btn = QPushButton("Kopiuj rozpoznane dane")
        kopiuj_btn.clicked.connect(self.kopiuj_rozpoznane_dane)
        preview_layout.addWidget(kopiuj_btn)
        
        # Ustawienie układu
        layout.addLayout(preview_layout)
        
        # Przyciski
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Wypełnienie wartościami, jeśli zostały rozpoznane
        if self.debug_info['numer_zlecenia'] != "NIEZNANY":
            self.numer_zlecenia_edit.setText(self.debug_info['numer_zlecenia'])
        
        if self.debug_info['numer_operatora'] != "NIEZNANY":
            self.numer_operatora_edit.setText(self.debug_info['numer_operatora'])
        
        if self.debug_info['data_raportu'] != "NIEZNANA":
            self.data_raportu_edit.setText(self.debug_info['data_raportu'])
    
    def create_readonly_field(self, text):
        """Tworzenie pola tylko do odczytu z rozpoznaną wartością."""
        field = QLineEdit(text)
        field.setReadOnly(True)
        field.setStyleSheet("background-color: #f0f0f0;")
        return field
    
    def kopiuj_rozpoznane_dane(self):
        """Kopiowanie rozpoznanych danych do pól edycji."""
        self.numer_zlecenia_edit.setText(self.debug_info['numer_zlecenia'])
        self.numer_operatora_edit.setText(self.debug_info['numer_operatora'])
        self.data_raportu_edit.setText(self.debug_info['data_raportu'])
    
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