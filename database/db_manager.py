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
    
    def simpan_riwayat_grafik(self, subjek_id, tanggal, blob_gambar, analisis_teks=""):
        """Menyimpan data biner screenshot ke tabel riwayat dengan context manager yang benar"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS riwayat_grafik (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        subjek_id INTEGER,
                        tanggal TEXT,
                        screenshot BLOB,
                        analisis TEXT
                    )
                """)
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
            return None
    
    def update_analisis_saja(self, subjek_id, teks_baru):
        """Memperbarui teks analisis saja tanpa mengubah gambar screenshot yang sudah ada"""
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
        """Menghapus total data subjek dan riwayat grafiknya secara sinkron dari database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                # PERBAIKAN: Nama tabel disesuaikan dari 'subjek' menjadi 'subjects' sesuai init_db
                cursor.execute("DELETE FROM subjects WHERE id = ?", (subjek_id,))
                # Hapus riwayat gambar pendukungnya
                cursor.execute("DELETE FROM riwayat_grafik WHERE subjek_id = ?", (subjek_id,))
                conn.commit()
                print(f"🗑️ Rekaman ID #{subjek_id} beserta grafiknya sukses dihapus permanen.")
        except Exception as e:
            print(f"❌ Database Error (hapus_rekaman): {e}")