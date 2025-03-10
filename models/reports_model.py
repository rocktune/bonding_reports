# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant


class ReportsTableModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
        self._headers = ["ID", "Numer zlecenia", "Numer operatora", "Data raportu", "Ścieżka PDF", "Data importu"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._data)):
            return QVariant()
        
        if role == Qt.DisplayRole:
            return str(self._data[index.row()][index.column()])
            
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return QVariant()
    
    def sort(self, column, order):
        """Sortowanie danych modelu."""
        self.layoutAboutToBeChanged.emit()
        self._data = sorted(self._data, key=lambda x: x[column], reverse=(order == Qt.DescendingOrder))
        self.layoutChanged.emit()

    def update_data(self, data):
        """Aktualizacja danych modelu."""
        self.layoutAboutToBeChanged.emit()
        self._data = data
        self.layoutChanged.emit()
        
    def get_row_data(self, row):
        """Pobieranie danych z określonego wiersza."""
        if 0 <= row < len(self._data):
            return self._data[row]
        return None