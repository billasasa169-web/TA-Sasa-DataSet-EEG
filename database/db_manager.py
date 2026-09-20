# database/db_manager.py

import sqlite3
import os

class DBManager:
    def __init__(self, db_name="eeg_app.db"):
        # 1. Cari tahu lokasi folder absolut dari file db_manager.py ini berada
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Gabungkan lokasi folder tersebut dengan nama file database
        self.db_path = os.path.join(current_dir, db_name)
        
        # 3. Jalankan inisialisasi pembuatan tabel
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Membuat tabel jika belum ada saat aplikasi pertama kali dijalankan"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Tabel Utama Subjek
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
            # 2. Tabel Riwayat Grafik (Dibuat otomatis di sini agar tidak error no such table)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS riwayat_grafik (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subjek_id INTEGER,
                    tanggal TEXT,
                    screenshot BLOB,
                    analisis TEXT,
                    FOREIGN KEY (subjek_id) REFERENCES subjects (id) ON DELETE CASCADE
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
        """
        PERBAIKAN: Mengambil seluruh 7 kolom data subjek sesuai urutan struktur DB riil
        0: id, 1: nama, 2: umur, 3: alamat, 4: email, 5: jenis_kelamin, 6: created_at
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nama, umur, alamat, email, jenis_kelamin, created_at FROM subjects ORDER BY id DESC")
            return cursor.fetchall()
    
    def simpan_riwayat_grafik(self, subjek_id, tanggal, blob_gambar, analisis_teks=""):
        """Menyimpan data biner screenshot ke tabel riwayat"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO riwayat_grafik (subjek_id, tanggal, screenshot, analisis) VALUES (?, ?, ?, ?)",
                    (subjek_id, tanggal, blob_gambar, analisis_teks)
                )
                conn.commit()
                print("✅ [SQLITE SUCCESS] Screenshot grafik berhasil disimpan ke database!")
        except Exception as e:
            print(f"❌ Database Error (simpan_riwayat_grafik): {e}")

    def ambil_screenshot_terakhir(self, subjek_id):
        """Mengambil data screenshot PNG biner terbaru berdasarkan ID subjek"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT screenshot, analisis FROM riwayat_grafik WHERE subjek_id = ? ORDER BY id DESC LIMIT 1",
                    (subjek_id,)
                )
                res = cursor.fetchone()
                return res if res else (None, "")
        except Exception as e:
            print(f"❌ Database Error (ambil_screenshot_terakhir): {e}")
            return (None, "")
    
    def update_analisis_saja(self, subjek_id, teks_baru):
        """Memperbarui teks analisis saja tanpa mengubah gambar screenshot"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE riwayat_grafik SET analisis = ? WHERE id = (SELECT id FROM riwayat_grafik WHERE subjek_id = ? ORDER BY id DESC LIMIT 1)",
                    (teks_baru, subjek_id)
                )
                conn.commit()
                print("✅ [SQLITE SUCCESS] Teks analisis berhasil diperbarui!")
                return True
        except Exception as e:
            print(f"❌ Database Error (update_analisis_saja): {e}")
            return False

    def hapus_rekaman_subjek(self, subjek_id):
        """Menghapus total data subjek dan riwayat grafiknya secara sinkron"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM subjects WHERE id = ?", (subjek_id,))
                cursor.execute("DELETE FROM riwayat_grafik WHERE subjek_id = ?", (subjek_id,))
                conn.commit()
                print(f"🗑️ Rekaman ID #{subjek_id} beserta grafiknya sukses dihapus permanen.")
        except Exception as e:
            print(f"❌ Database Error (hapus_rekaman): {e}")