# database/db_manager.py

import sqlite3
import os

class DBManager:
    def __init__(self, db_name="eeg_app.db"):
        # 1. Cari tahu lokasi folder absolut dari file db_manager.py ini berada
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Gabungkan lokasi folder tersebut dengan nama file database
        # Hasilnya akan mengarah pasti ke: .../TA-SASA-DATASET-EEG/database/eeg_app.db
        self.db_path = os.path.join(current_dir, db_name)
        
        # 3. Jalankan inisialisasi pembuatan tabel
        self.init_db()

    def get_connection(self):
        # Menggunakan db_path (jalur absolut ke dalam folder database)
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Membuat tabel jika belum ada saat aplikasi pertama kali dijalankan"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama TEXT NOT NULL,
                    umur INTEGER NOT NULL,
                    alamat TEXT,
                    email TEXT,
                    jenis_kelamin TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_subject(self, nama, umur, alamat, email, jenis_kelamin):
        """Menyimpan data subjek baru ke SQLite"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO subjects (nama, umur, alamat, email, jenis_kelamin)
                    VALUES (?, ?, ?, ?, ?)
                """, (nama, umur, alamat, email, jenis_kelamin))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Database Error: {e}")
            return None

    def get_all_subjects(self):
        """Mengambil riwayat semua subjek"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nama, umur, jenis_kelamin, created_at FROM subjects ORDER BY id DESC")
            return cursor.fetchall()