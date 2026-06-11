# ui/form_page.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QButtonGroup, QFormLayout, QMessageBox
from PyQt5.QtCore import Qt

class FormPage(QWidget):
    def __init__(self, db_manager, on_success_callback):
        super().__init__()
        self.db_manager = db_manager
        self.on_success_callback = on_success_callback
        self.init_ui()

    def init_ui(self):
        # Layout Utama Halaman
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setAlignment(Qt.AlignTop)

        # Elemen Teks Judul (Dipaksa Rata Tengah / Center Alignment)
        self.title = QLabel("INPUT DATA SUBJEK / PASIEN")
        self.title.setAlignment(Qt.AlignCenter) 
        self.main_layout.addWidget(self.title)

        # Wadah Utama Form agar Berada di Tengah Halaman (Horizontal Stretching)
        form_container = QHBoxLayout()
        self.form_layout = QFormLayout()
        self.form_layout.setHorizontalSpacing(24)
        self.form_layout.setVerticalSpacing(18)

        # Inisialisasi Input Field
        self.entry_nama = QLineEdit()
        self.entry_umur = QLineEdit()
        self.entry_alamat = QLineEdit()
        self.entry_email = QLineEdit()
        
        self.fields = [self.entry_nama, self.entry_umur, self.entry_alamat, self.entry_email]

        # Inisialisasi Label Form Kiri
        self.lbl_nama = QLabel("Nama Lengkap :")
        self.lbl_umur = QLabel("Umur (Tahun) :")
        self.lbl_alamat = QLabel("Alamat Tinggal :")
        self.lbl_email = QLabel("Email Pasien :")
        self.lbl_jk = QLabel("Jenis Kelamin :")
        
        self.labels = [self.lbl_nama, self.lbl_umur, self.lbl_alamat, self.lbl_email, self.lbl_jk]

        # Menyusun Baris Form Layout
        self.form_layout.addRow(self.lbl_nama, self.entry_nama)
        self.form_layout.addRow(self.lbl_umur, self.entry_umur)
        self.form_layout.addRow(self.lbl_alamat, self.entry_alamat)
        self.form_layout.addRow(self.lbl_email, self.entry_email)

        # Radio Button Gender Kompatibel
        self.laki_radio = QRadioButton("Laki-laki")
        self.perempuan_radio = QRadioButton("Perempuan")
        self.jk_group = QButtonGroup()
        self.jk_group.addButton(self.laki_radio)
        self.jk_group.addButton(self.perempuan_radio)

        self.jk_layout = QHBoxLayout()
        self.jk_layout.addWidget(self.laki_radio)
        self.jk_layout.addWidget(self.perempuan_radio)
        self.jk_layout.addStretch()
        
        self.form_layout.addRow(self.lbl_jk, self.jk_layout)

        form_container.addStretch()
        form_container.addLayout(self.form_layout)
        form_container.addStretch()
        self.main_layout.addLayout(form_container)

        self.main_layout.addSpacing(20)

        # Tombol Aksi Submit Data
        self.submit_btn = QPushButton("Simpan")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self.save_data)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.submit_btn)
        btn_layout.addStretch()
        self.main_layout.addLayout(btn_layout)

    def resizeEvent(self, event):
        """Mekanisme Media Query Dinamis Sisi Form - Sinkron dengan MainWindow"""
        current_width = event.size().width()
        
        if current_width >= 1340: 
            self.apply_form_media_styles(is_large=True)
        else:
            self.apply_form_media_styles(is_large=False)
            
        super().resizeEvent(event)

    def apply_form_media_styles(self, is_large):
        """Penerapan Aturan Skalabilitas Ukuran Komponen Form Secara Otomatis"""
        if is_large:
            font_title = "20pt"
            font_label = "12pt"
            font_input = "12pt"
            input_min_width = 480
            input_height = 45
            btn_width = 280
            btn_height = 54
            vertical_spacing = 24
            
            # Tambahkan margin atas yang besar saat window di-maximize
            title_margin_top = "60px"
            title_margin_bottom = "40px"
        else:
            font_title = "17pt"
            font_label = "10.5pt"
            font_input = "10pt"
            input_min_width = 360
            input_height = 36
            btn_width = 210
            btn_height = 42
            vertical_spacing = 16
            
            # Gunakan margin standar saat window berukuran normal (kecil)
            title_margin_top = "0px"
            title_margin_bottom = "25px"

        self.form_layout.setVerticalSpacing(vertical_spacing)

        # Update Font Style & Margin Atas/Bawah pada Judul Secara Dinamis
        self.title.setStyleSheet(f"""
            QLabel {{
                font-size: {font_title}; 
                font-weight: 800; 
                color: #0284c7; 
                margin-top: {title_margin_top}; 
                margin-bottom: {title_margin_bottom};
            }}
        """)
        
        for lbl in self.labels:
            lbl.setStyleSheet(f"font-size: {font_label}; font-weight: 600; color: #475569;")

        for entry in self.fields:
            entry.setMinimumWidth(input_min_width)
            entry.setFixedHeight(input_height)
            entry.setStyleSheet(f"""
                QLineEdit {{
                    font-size: {font_input};
                    padding-left: 10px;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    background-color: white;
                }}
                QLineEdit:focus {{
                    border: 2px solid #0284c7;
                    background-color: #f8fafc;
                }}
            """)

        radio_qss = f"QRadioButton {{ font-size: {font_input}; font-weight: 500; color: #334155; padding-left: 5px; }} QRadioButton::indicator {{ width: { '20px' if is_large else '16px' }; height: { '20px' if is_large else '16px' }; }}"
        self.laki_radio.setStyleSheet(radio_qss)
        self.perempuan_radio.setStyleSheet(radio_qss)

        self.submit_btn.setFixedSize(btn_width, btn_height)
        self.submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #0284c7;
                color: white;
                font-size: {font_label};
                font-weight: 700;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: #0369a1;
            }}
            QPushButton:pressed {{
                background-color: #075985;
            }}
        """)

    def save_data(self):
        nama = self.entry_nama.text().strip()
        umur_str = self.entry_umur.text().strip()
        alamat = self.entry_alamat.text().strip()
        email = self.entry_email.text().strip()
        jk = "Laki-laki" if self.laki_radio.isChecked() else "Perempuan" if self.perempuan_radio.isChecked() else ""

        if not (nama and umur_str and jk):
            QMessageBox.warning(self, "Validasi Gagal", "Komponen utama (Nama, Umur, Jenis Kelamin) wajib diisi medis!")
            return

        try:
            umur = int(umur_str)
        except ValueError:
            QMessageBox.critical(self, "Validasi Gagal", "Karakter umur harus berupa bilangan angka numerik!")
            return

        sub_id = self.db_manager.add_subject(nama, umur, alamat, email, jk)
        if sub_id:
            QMessageBox.information(self, "Sukses", "Data subjek berhasil disimpan")
            
            self.entry_nama.clear()
            self.entry_umur.clear()
            self.entry_alamat.clear()
            self.entry_email.clear()
            self.jk_group.setExclusive(False)
            self.laki_radio.setChecked(False)
            self.perempuan_radio.setChecked(False)
            self.jk_group.setExclusive(True)
            
            self.on_success_callback({
                "id": sub_id, 
                "nama": nama, 
                "umur": umur, 
                "alamat": alamat, 
                "email": email, 
                "jenis_kelamin": jk
            })