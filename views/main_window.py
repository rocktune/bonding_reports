# -*- coding: utf-8 -*-

import os
import re
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QFileDialog, QTableView, QHeaderView, QMessageBox,
                            QLabel, QLineEdit, QComboBox, QGroupBox, QFormLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

from database.db_manager import DatabaseManager
from controllers.pdf_processor import PDFProcessor
from models.reports_model import ReportsTableModel
# Importy dialogów są wywołane w metodach, aby uniknąć cyklicznych importów


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inicjalizacja menedżera bazy danych i procesora PDF
        self.db_manager = DatabaseManager()
        self.pdf_processor = PDFProcessor(self.db_manager)
        
        # Inicjalizacja interfejsu użytkownika
        self.init_ui()
        
        # Wczytanie raportów
        self.load_reports()

    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika."""
        self.setWindowTitle("System zarządzania raportami Klejenia")
        self.setGeometry(100, 100, 1000, 600)
        
        # Główny widget i układ
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Grupa przycisków
        button_layout = QHBoxLayout()
        self.import_btn = QPushButton("Importuj PDF")
        self.import_btn.clicked.connect(self.import_pdf)
        button_layout.addWidget(self.import_btn)
        
        self.edit_btn = QPushButton("Edytuj")
        self.edit_btn.clicked.connect(self.edit_report)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Usuń")
        self.delete_btn.clicked.connect(self.delete_report)
        button_layout.addWidget(self.delete_btn)
        
        self.create_template_btn = QPushButton("Utwórz szablon rozpoznawania")
        self.create_template_btn.clicked.connect(self.create_template)
        button_layout.addWidget(self.create_template_btn)
        
        # Wyszukiwanie i filtrowanie
        search_filter_layout = QHBoxLayout()
        
        # Grupa wyszukiwania
        search_group = QGroupBox("Wyszukiwanie")
        search_form = QFormLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Wpisz tekst...")
        self.search_edit.textChanged.connect(self.search_reports)
        search_form.addRow("Szukaj:", self.search_edit)
        search_group.setLayout(search_form)
        search_filter_layout.addWidget(search_group)
        
        # Grupa filtrowania
        filter_group = QGroupBox("Filtrowanie po segmencie")
        filter_form = QFormLayout()
        
        self.segment_combo = QComboBox()
        self.segment_combo.addItems(["Segment 1", "Segment 2", "Segment 3", "Segment 4"])
        filter_form.addRow("Wybierz segment:", self.segment_combo)
        
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Wpisz wartość segmentu...")
        self.filter_edit.textChanged.connect(self.filter_reports)
        filter_form.addRow("Filtruj:", self.filter_edit)
        
        filter_group.setLayout(filter_form)
        search_filter_layout.addWidget(filter_group)
        
        # Tabela raportów
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.table_view.doubleClicked.connect(self.open_pdf)
        
        # Dostosowanie szerokości kolumn
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        # Ułożenie elementów w głównym układzie
        main_layout.addLayout(button_layout)
        main_layout.addLayout(search_filter_layout)
        main_layout.addWidget(self.table_view)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def import_pdf(self):
        """Importowanie pliku PDF."""
        # Import dialogu tworzenia szablonu lokalnie aby uniknąć cyklicznych importów
        from views.dialogs.template_dialog import TemplateCreatorDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik PDF", "", "Pliki PDF (*.pdf)"
        )
        
        if file_path:
            # Sprawdzenie, czy istnieje szablon
            template = self.db_manager.get_template()
            if not template:
                # Zapytaj, czy chcesz utworzyć szablon
                result = QMessageBox.question(
                    self, "Brak szablonu rozpoznawania", 
                    "Nie znaleziono szablonu rozpoznawania dokumentów. Czy chcesz utworzyć szablon teraz?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if result == QMessageBox.Yes:
                    dialog = TemplateCreatorDialog(file_path, self.db_manager, self)
                    if dialog.exec_() != dialog.Accepted:
                        return
            
            try:
                # Przetwarzanie pliku PDF
                numer_zlecenia, numer_operatora, data_raportu = self.pdf_processor.extract_data_from_pdf(file_path)
                
                # Jeśli użytkownik anulował import, zakończ
                if numer_zlecenia is None:
                    return
                
                # Sprawdzenie ścieżki PDF (mogła zostać zmieniona w dialogu)
                pdf_path = file_path
                if hasattr(self, 'current_pdf_path') and self.current_pdf_path:
                    pdf_path = self.current_pdf_path
                
                # Zapisanie danych w bazie
                self.db_manager.insert_report(numer_zlecenia, numer_operatora, data_raportu, pdf_path)
                
                # Odświeżenie widoku
                self.load_reports()
                
                QMessageBox.information(
                    self, "Sukces", f"Pomyślnie zaimportowano raport:\nNumer zlecenia: {numer_zlecenia}\nOperator: {numer_operatora}\nData: {data_raportu}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Błąd", f"Wystąpił błąd podczas importowania pliku:\n{str(e)}"
                )

    def create_template(self):
        """Tworzenie szablonu rozpoznawania dokumentów."""
        # Import dialogu lokalnie aby uniknąć cyklicznych importów
        from views.dialogs.template_dialog import TemplateCreatorDialog
        
        # Wybór pliku PDF do utworzenia szablonu
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz przykładowy PDF", "", "Pliki PDF (*.pdf)"
        )
        
        if file_path:
            dialog = TemplateCreatorDialog(file_path, self.db_manager, self)
            dialog.exec_()

    def load_reports(self):
        """Ładowanie wszystkich raportów do tabeli."""
        reports = self.db_manager.get_all_reports()
        self.update_table_model(reports)

    def search_reports(self):
        """Wyszukiwanie raportów."""
        search_text = self.search_edit.text()
        if search_text:
            reports = self.db_manager.search_reports(search_text)
        else:
            reports = self.db_manager.get_all_reports()
        self.update_table_model(reports)

    def filter_reports(self):
        """Filtrowanie raportów według segmentu numeru zlecenia."""
        segment_index = self.segment_combo.currentIndex() + 1  # Indeksowanie od 1
        filter_value = self.filter_edit.text()
        
        if filter_value:
            reports = self.db_manager.filter_by_segment(segment_index, filter_value)
        else:
            reports = self.db_manager.get_all_reports()
        
        self.update_table_model(reports)

    def update_table_model(self, data):
        """Aktualizacja modelu danych tabeli."""
        self.table_model = ReportsTableModel(data)
        self.table_view.setModel(self.table_model)
        
        # Ukrycie kolumny z pełną ścieżką do pliku PDF (ale zachowanie danych)
        self.table_view.setColumnHidden(4, True)

    def open_pdf(self, index):
        """Otwieranie pliku PDF po dwukrotnym kliknięciu w wiersz."""
        row = index.row()
        # Pobranie ścieżki do pliku z kolumny 4 (ukryta)
        pdf_path = self.table_model._data[row][4]
        
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))
        else:
            QMessageBox.warning(
                self, "Ostrzeżenie", "Nie można znaleźć pliku PDF. Być może został przeniesiony lub usunięty."
            )

    def edit_report(self):
        """Edycja wybranego raportu."""
        # Import dialogu edycji lokalnie aby uniknąć cyklicznych importów
        from views.dialogs.edit_dialog import EditReportDialog
        
        # Sprawdzenie, czy wybrano raport
        selection = self.table_view.selectionModel()
        if not selection.hasSelection():
            QMessageBox.warning(self, "Ostrzeżenie", "Najpierw wybierz raport do edycji.")
            return
        
        # Pobranie ID wybranego raportu
        row = selection.currentIndex().row()
        report_id = self.table_model._data[row][0]  # ID znajduje się w pierwszej kolumnie
        
        # Pobranie danych raportu
        report_data = self.db_manager.get_report_by_id(report_id)
        if not report_data:
            QMessageBox.critical(self, "Błąd", "Nie można pobrać danych raportu.")
            return
        
        # Utworzenie i wyświetlenie dialogu edycji
        dialog = EditReportDialog(self, report_data)
        if dialog.exec_() == dialog.Accepted:
            # Pobranie edytowanych danych
            edited_data = dialog.get_edited_data()
            
            # Walidacja numeru zlecenia
            numer_zlecenia_pattern = r'^[A-Z0-9]{3}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{3}$'
            if not re.match(numer_zlecenia_pattern, edited_data['numer_zlecenia']):
                QMessageBox.warning(
                    self, "Błędny format", 
                    "Numer zlecenia musi być w formacie XXX-XXXX-XXXX-XXX"
                )
                return
            
            # Aktualizacja danych w bazie
            try:
                self.db_manager.update_report(
                    report_id,
                    edited_data['numer_zlecenia'],
                    edited_data['numer_operatora'],
                    edited_data['data_raportu'],
                    edited_data['sciezka_pdf']
                )
                
                # Odświeżenie widoku
                self.load_reports()
                
                QMessageBox.information(self, "Sukces", "Pomyślnie zaktualizowano dane raportu.")
                
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas aktualizacji danych:\n{str(e)}")
    
    def delete_report(self):
        """Usuwanie wybranego raportu."""
        # Sprawdzenie, czy wybrano raport
        selection = self.table_view.selectionModel()
        if not selection.hasSelection():
            QMessageBox.warning(self, "Ostrzeżenie", "Najpierw wybierz raport do usunięcia.")
            return
        
        # Pobranie ID wybranego raportu
        row = selection.currentIndex().row()
        report_id = self.table_model._data[row][0]  # ID znajduje się w pierwszej kolumnie
        numer_zlecenia = self.table_model._data[row][1]  # Numer zlecenia
        
        # Potwierdzenie usunięcia
        result = QMessageBox.question(
            self, "Potwierdzenie usunięcia", 
            f"Czy na pewno chcesz usunąć raport\nnumer zlecenia: {numer_zlecenia}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if result == QMessageBox.Yes:
            try:
                # Usunięcie raportu z bazy danych
                success = self.db_manager.delete_report(report_id)
                
                if success:
                    # Odświeżenie widoku
                    self.load_reports()
                    
                    QMessageBox.information(self, "Sukces", "Pomyślnie usunięto raport.")
                else:
                    QMessageBox.warning(self, "Ostrzeżenie", "Nie udało się usunąć raportu.")
                
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Wystąpił błąd podczas usuwania raportu:\n{str(e)}")
    
    def closeEvent(self, event):
        """Obsługa zdarzenia zamknięcia okna."""
        self.db_manager.close()
        event.accept()