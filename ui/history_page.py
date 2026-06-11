# ui/history_page.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QHeaderView, QMessageBox
from PyQt5.QtCore import Qt

class HistoryPage(QWidget):
    def __init__(self, db_manager, on_select_patient_callback):
        super().__init__()
        self.db_manager = db_manager
        self.on_select_patient_callback = on_select_patient_callback 
        self.current_is_large = False  # Menyimpan status ukuran layar aktif untuk generator baris tabel
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(20)

        # Elemen Teks Judul (Dipaksa Rata Tengah / Center Alignment)
        self.title = QLabel("RIWAYAT DAN DAFTAR SUBJEK / PASIEN")
        self.title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title)

        # Tabel Utama Pasien dengan Tampilan User Friendly & Modern Clinical
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Nama Pasien", "Umur", "Jenis Kelamin", "Tanggal Input", "Aksi"])
        
        # Pengaturan Grid Tabel agar Rapi dan Terstruktur
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.Stretch)          
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch) # Diubah ke Stretch agar kontainer tombol memiliki ruang center sempurna
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setShowGrid(False)  # Menghilangkan garis pembatas kaku agar tampilan modern kustom
        self.table.verticalHeader().setVisible(False)

        self.main_layout.addWidget(self.table)

        # Tombol Refresh manual di bawah tabel
        self.btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Perbarui Daftar")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_patient_data)
        
        self.btn_layout.addWidget(self.refresh_btn)
        self.btn_layout.addStretch()
        self.main_layout.addLayout(self.btn_layout)

    def resizeEvent(self, event):
        """Mekanisme Media Query Dinamis Sisi Tabel - Sinkron dengan Jendela Utama"""
        current_width = event.size().width()
        
        # Mengikuti breakpoint resolusi besar 1600px (dikurangi estimasi lebar sidebar)
        if current_width >= 1340:
            self.apply_history_media_styles(is_large=True)
        else:
            self.apply_history_media_styles(is_large=False)
            
        super().resizeEvent(event)

    def apply_history_media_styles(self, is_large):
        """Penerapan Aturan Skalabilitas Teks, Baris Tabel, dan Tombol Refresh"""
        self.current_is_large = is_large  # Amankan status resolusi untuk rendering tombol sel
        
        if is_large:
            font_title = "20pt"
            font_table = "11pt"
            font_btn = "12pt"
            
            row_height = 65        
            header_height = 58     
            
            refresh_btn_width = 300
            refresh_btn_height = 50
            title_margin_top = "60px"
            title_margin_bottom = "30px"
        else:
            font_title = "17pt"
            font_table = "10pt"
            font_btn = "10.5pt"
            
            row_height = 52        
            header_height = 46     
            
            refresh_btn_width = 200
            refresh_btn_height = 38
            title_margin_top = "0px"
            title_margin_bottom = "15px"

        # 1. Update Margin dan Font Teks Judul Utama (Rata Tengah)
        self.title.setStyleSheet(f"""
            QLabel {{
                font-size: {font_title}; 
                font-weight: 800; 
                color: #0284c7; 
                margin-top: {title_margin_top}; 
                margin-bottom: {title_margin_bottom};
            }}
        """)

        # 2. Update Desain Header dan Baris Tabel Secara Profesional
        self.table.horizontalHeader().setFixedHeight(header_height)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                font-size: {font_table};
            }}
            QTableWidget::item {{
                padding-left: 20px;
                padding-right: 20px;
                border-bottom: 1px solid #f1f5f9;
            }}
            QHeaderView::section {{
                background-color: #1e293b;
                color: #f8fafc;
                font-weight: 700;
                font-size: {font_table};
                border: none;
            }}
        """)

        # Mengubah tinggi baris yang sudah ada di dalam tabel secara dinamis
        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, row_height)
            
            # Cari widget internal pembungkus tombol di kolom 5
            container_widget = self.table.cellWidget(i, 5)
            if container_widget:
                # Ambil tombol Detail asli dari dalam layout kontainer widget
                btn_actual = container_widget.findChild(QPushButton)
                if btn_actual:
                    self.style_action_button(btn_actual, is_large, font_table)

        # 3. Update Dimensi & Desain Tombol Refresh Daftar
        self.refresh_btn.setFixedSize(refresh_btn_width, refresh_btn_height)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #475569;
                color: white;
                font-size: {font_btn};
                font-weight: 700;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{ background-color: #334155; }}
            QPushButton:pressed {{ background-color: #1e293b; }}
        """)

    def style_action_button(self, button, is_large, font_size):
        """Utility khusus untuk merestrukturisasi skala ukuran tombol sel uji sinyal"""
        btn_width = 130 if is_large else 105
        btn_height = 38 if is_large else 32  
        button.setFixedSize(btn_width, btn_height)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: #0284c7; 
                color: white; 
                border-radius: 6px; 
                font-weight: 700; 
                font-size: {font_size};
                border: none;
            }}
            QPushButton:hover {{ background-color: #0369a1; }}
            QPushButton:pressed {{ background-color: #075985; }}
        """)

    def load_patient_data(self):
        """Menarik data dari SQLite dan memasukkannya ke dalam baris tabel secara dinamis"""
        self.table.setRowCount(0)
        patients = self.db_manager.get_all_subjects()
        
        if not patients:
            return

        self.table.setRowCount(len(patients))
        
        row_height = 65 if self.current_is_large else 52
        font_table = "11pt" if self.current_is_large else "10pt"
        
        for row_idx, patient in enumerate(patients):
            sub_id, nama, umur, jk, tanggal = patient
            
            patient_dict = {
                "id": sub_id,
                "nama": nama,
                "umur": umur,
                "jenis_kelamin": jk,
                "alamat": "-", 
                "email": "-"
            }

            self.table.setRowHeight(row_idx, row_height)

            # 1. Membuat Item Sel Data Pasien
            item_id = QTableWidgetItem(f"#{sub_id}")
            item_nama = QTableWidgetItem(nama)
            item_umur = QTableWidgetItem(f"{umur} Tahun")
            item_jk = QTableWidgetItem(jk)
            item_tanggal = QTableWidgetItem(str(tanggal))

            # 2. Set Seluruh Komponen Teks Menjadi Rata Tengah (Center Alignment)
            for item in [item_id, item_nama, item_umur, item_jk, item_tanggal]:
                item.setTextAlignment(Qt.AlignCenter)

            # Masukkan item terformat rata tengah ke tabel
            self.table.setItem(row_idx, 0, item_id)
            self.table.setItem(row_idx, 1, item_nama)
            self.table.setItem(row_idx, 2, item_umur)
            self.table.setItem(row_idx, 3, item_jk)
            self.table.setItem(row_idx, 4, item_tanggal)

            # 3. Solusi Rata Tengah Vertikal Tombol Detail Menggunakan Kontainer Centered Layout
            btn_test = QPushButton("Detail")  
            btn_test.setCursor(Qt.PointingHandCursor)
            self.style_action_button(btn_test, self.current_is_large, font_table)
            
            # Hubungkan fungsi callback klik
            btn_test.clicked.connect(lambda checked, p=patient_dict: self.on_select_patient_callback(p))
            
            # Buat QWidget kosong sebagai jembatan pembungkus tombol
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.addWidget(btn_test)
            
            # Set margin internal 0 dan gunakan alignment total tengah (Menciptakan ruang gap atas-bawah simetris)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setAlignment(Qt.AlignCenter)
            
            # Masukkan kontainer pelindung tersebut ke kolom aksi (indeks ke-5)
            self.table.setCellWidget(row_idx, 5, container)