# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QFormLayout, QDialogButtonBox, QFileDialog)
from PyQt5.QtCore import Qt


class ManualDataEntryDialog(QDialog):
    """Dialog do ręcznego wprowadzania danych, gdy automatyczna ekstrakcja zawiedzie."""
    def __init__(self, parent=None, pdf_path=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
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