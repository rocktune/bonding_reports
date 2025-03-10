# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                            QLineEdit, QFormLayout, QDialogButtonBox, QFileDialog)
from PyQt5.QtCore import Qt


class EditReportDialog(QDialog):
    """Dialog do edycji istniejącego raportu."""
    def __init__(self, parent=None, report_data=None):
        super().__init__(parent)
        self.report_data = report_data
        self.init_ui()
        
    def init_ui(self):
        """Inicjalizacja interfejsu dialogu edycji."""
        self.setWindowTitle("Edycja raportu")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Formularz edycji
        form_layout = QFormLayout()
        
        self.numer_zlecenia_edit = QLineEdit()
        self.numer_operatora_edit = QLineEdit()
        self.data_raportu_edit = QLineEdit()
        
        # Wypełnienie pól danymi
        if self.report_data:
            self.numer_zlecenia_edit.setText(self.report_data[1])  # numer_zlecenia
            self.numer_operatora_edit.setText(self.report_data[2])  # numer_operatora
            self.data_raportu_edit.setText(self.report_data[3])  # data_raportu
            
            # Ścieżka PDF
            self.sciezka_pdf_edit = QLineEdit(self.report_data[4])
            self.sciezka_pdf_edit.setReadOnly(True)
            
            browse_btn = QPushButton("Zmień...")
            browse_btn.clicked.connect(self.browse_pdf)
            
            path_layout = QHBoxLayout()
            path_layout.addWidget(self.sciezka_pdf_edit)
            path_layout.addWidget(browse_btn)
        
        form_layout.addRow("Numer zlecenia:", self.numer_zlecenia_edit)
        form_layout.addRow("Numer operatora:", self.numer_operatora_edit)
        form_layout.addRow("Data raportu:", self.data_raportu_edit)
        form_layout.addRow("Ścieżka do pliku PDF:", path_layout)
        
        # Dodanie formularza do głównego układu
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
    
    def get_edited_data(self):
        """Zwraca edytowane dane."""
        return {
            'numer_zlecenia': self.numer_zlecenia_edit.text(),
            'numer_operatora': self.numer_operatora_edit.text(),
            'data_raportu': self.data_raportu_edit.text(),
            'sciezka_pdf': self.sciezka_pdf_edit.text()
        }