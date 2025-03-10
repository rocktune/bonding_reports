# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime
import config


class DatabaseManager:
    def __init__(self, db_name=config.DB_NAME):
        """Inicjalizacja menedżera bazy danych."""
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Tworzenie tabeli raportów jeśli nie istnieje."""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS raporty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numer_zlecenia TEXT NOT NULL,
            numer_operatora TEXT NOT NULL,
            data_raportu TEXT NOT NULL,
            segment1 TEXT,
            segment2 TEXT,
            segment3 TEXT,
            segment4 TEXT,
            sciezka_pdf TEXT NOT NULL,
            data_importu TEXT NOT NULL
        )
        ''')
        
        # Tabela dla szablonów rozpoznawania
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS szablony (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nazwa TEXT NOT NULL,
            roi_numer_zlecenia TEXT,
            roi_numer_operatora TEXT,
            roi_data TEXT
        )
        ''')
        
        self.conn.commit()

    def insert_report(self, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf):
        """Wstawianie nowego raportu do bazy danych."""
        # Podział numeru zlecenia na segmenty
        segments = numer_zlecenia.split('-')
        segment1, segment2, segment3, segment4 = '', '', '', ''
        
        if len(segments) >= 1:
            segment1 = segments[0]
        if len(segments) >= 2:
            segment2 = segments[1]
        if len(segments) >= 3:
            segment3 = segments[2]
        if len(segments) >= 4:
            segment4 = segments[3]
            
        data_importu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.cursor.execute('''
        INSERT INTO raporty (numer_zlecenia, numer_operatora, data_raportu, 
                           segment1, segment2, segment3, segment4,
                           sciezka_pdf, data_importu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (numer_zlecenia, numer_operatora, data_raportu, 
              segment1, segment2, segment3, segment4,
              sciezka_pdf, data_importu))
        self.conn.commit()

    def get_all_reports(self):
        """Pobieranie wszystkich raportów z bazy danych."""
        self.cursor.execute('''
        SELECT id, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf, data_importu
        FROM raporty
        ORDER BY data_importu DESC
        ''')
        return self.cursor.fetchall()
        
    def get_report_by_id(self, report_id):
        """Pobieranie danych raportu po ID."""
        self.cursor.execute('''
        SELECT id, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf
        FROM raporty
        WHERE id = ?
        ''', (report_id,))
        return self.cursor.fetchone()
        
    def update_report(self, report_id, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf=None):
        """Aktualizacja danych raportu."""
        # Podział numeru zlecenia na segmenty
        segments = numer_zlecenia.split('-')
        segment1, segment2, segment3, segment4 = '', '', '', ''
        
        if len(segments) >= 1:
            segment1 = segments[0]
        if len(segments) >= 2:
            segment2 = segments[1]
        if len(segments) >= 3:
            segment3 = segments[2]
        if len(segments) >= 4:
            segment4 = segments[3]
        
        if sciezka_pdf:
            self.cursor.execute('''
            UPDATE raporty 
            SET numer_zlecenia = ?, numer_operatora = ?, data_raportu = ?,
                segment1 = ?, segment2 = ?, segment3 = ?, segment4 = ?,
                sciezka_pdf = ?
            WHERE id = ?
            ''', (numer_zlecenia, numer_operatora, data_raportu, 
                  segment1, segment2, segment3, segment4, 
                  sciezka_pdf, report_id))
        else:
            self.cursor.execute('''
            UPDATE raporty 
            SET numer_zlecenia = ?, numer_operatora = ?, data_raportu = ?,
                segment1 = ?, segment2 = ?, segment3 = ?, segment4 = ?
            WHERE id = ?
            ''', (numer_zlecenia, numer_operatora, data_raportu, 
                  segment1, segment2, segment3, segment4, report_id))
        
        self.conn.commit()
    
    def delete_report(self, report_id):
        """Usuwanie raportu z bazy danych."""
        self.cursor.execute('''
        DELETE FROM raporty
        WHERE id = ?
        ''', (report_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def search_reports(self, search_text):
        """Wyszukiwanie raportów na podstawie tekstu wyszukiwania."""
        search_param = f"%{search_text}%"
        self.cursor.execute('''
        SELECT id, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf, data_importu
        FROM raporty
        WHERE numer_zlecenia LIKE ? OR numer_operatora LIKE ? OR data_raportu LIKE ?
        ORDER BY data_importu DESC
        ''', (search_param, search_param, search_param))
        return self.cursor.fetchall()
    
    def filter_by_segment(self, segment_index, segment_value):
        """Filtrowanie raportów według segmentu numeru zlecenia."""
        segment_column = f"segment{segment_index}"
        segment_param = f"%{segment_value}%"
        
        self.cursor.execute(f'''
        SELECT id, numer_zlecenia, numer_operatora, data_raportu, sciezka_pdf, data_importu
        FROM raporty
        WHERE {segment_column} LIKE ?
        ORDER BY data_importu DESC
        ''', (segment_param,))
        return self.cursor.fetchall()
    
    def save_template(self, name, roi_numer_zlecenia, roi_numer_operatora, roi_data):
        """Zapisanie szablonu rozpoznawania."""
        # Najpierw usuwamy wszystkie wcześniejsze szablony, aby mieć tylko jeden aktywny
        self.cursor.execute('''
        DELETE FROM szablony
        ''')
        
        # Dodanie nowego szablonu
        self.cursor.execute('''
        INSERT INTO szablony (nazwa, roi_numer_zlecenia, roi_numer_operatora, roi_data)
        VALUES (?, ?, ?, ?)
        ''', (name, roi_numer_zlecenia, roi_numer_operatora, roi_data))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_template(self, template_id=None):
        """Pobieranie szablonu rozpoznawania."""
        if template_id:
            self.cursor.execute('''
            SELECT id, nazwa, roi_numer_zlecenia, roi_numer_operatora, roi_data
            FROM szablony
            WHERE id = ?
            ''', (template_id,))
            return self.cursor.fetchone()
        else:
            # Pobierz ostatni szablon
            self.cursor.execute('''
            SELECT id, nazwa, roi_numer_zlecenia, roi_numer_operatora, roi_data
            FROM szablony
            ORDER BY id DESC
            LIMIT 1
            ''')
            return self.cursor.fetchone()
    
    def close(self):
        """Zamknięcie połączenia z bazą danych."""
        self.conn.close()