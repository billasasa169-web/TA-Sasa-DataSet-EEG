# ui/history_page.py

from PyQt5.QtCore import Qt  
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHBoxLayout, 
                             QHeaderView, QMessageBox, QDialog, QFileDialog, 
                             QSizePolicy, QTextEdit)
import os

class HistoryPage(QWidget):
    def __init__(self, db_manager, on_select_patient_callback):
        super().__init__()
        self.db_manager = db_manager
        self.on_select_patient_callback = on_select_patient_callback 
        self.current_is_large = False
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(40, 40, 40, 40)
        self.main_layout.setSpacing(20)

        # Teks Judul Utama Rata Tengah
        self.title = QLabel("RIWAYAT DAN DAFTAR SUBJEK / PASIEN")
        self.title.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.title)

        # Tabel Utama (8 Kolom Presisi UI)
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Nama Pasien", "Umur", "Jenis Kelamin", "Email", "Tanggal Input", "Aksi", "Hapus"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nama
        header.setSectionResizeMode(2, QHeaderView.Stretch)          # Umur
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Jenis Kelamin
        header.setSectionResizeMode(4, QHeaderView.Stretch)          # Email
        header.setSectionResizeMode(5, QHeaderView.Stretch)          # Tanggal Input
        header.setSectionResizeMode(6, QHeaderView.Stretch)          # Aksi (Detail)
        header.setSectionResizeMode(7, QHeaderView.Stretch)          # Hapus
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        self.main_layout.addWidget(self.table)

        # Tombol Refresh Manual
        self.btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Perbarui Daftar")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_patient_data)
        
        self.btn_layout.addWidget(self.refresh_btn)
        self.btn_layout.addStretch()
        self.main_layout.addLayout(self.btn_layout)

    def resizeEvent(self, event):
        current_width = event.size().width()
        if current_width >= 1340:
            self.apply_history_media_styles(is_large=True)
        else:
            self.apply_history_media_styles(is_large=False)
            
        super().resizeEvent(event)

    def apply_history_media_styles(self, is_large):
        self.current_is_large = is_large
        
        if is_large:
            font_title, font_table, font_btn = "20pt", "11pt", "12pt"
            row_height, header_height = 65, 58
            refresh_btn_width, refresh_btn_height = 300, 50
            title_margin_top, title_margin_bottom = "60px", "30px"
        else:
            font_title, font_table, font_btn = "17pt", "10pt", "10.5pt"
            row_height, header_height = 52, 46
            refresh_btn_width, refresh_btn_height = 200, 38
            title_margin_top, title_margin_bottom = "0px", "15px"

        self.title.setStyleSheet(f"""
            QLabel {{
                font-size: {font_title}; 
                font-weight: 800; 
                color: #0284c7; 
                margin-top: {title_margin_top}; 
                margin-bottom: {title_margin_bottom};
            }}
        """)

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
            QTableWidget::section {{
                background-color: #1e293b;
                color: #f8fafc;
                font-weight: 700;
                font-size: {font_table};
                border: none;
            }}
        """)

        for i in range(self.table.rowCount()):
            self.table.setRowHeight(i, row_height)
            
            # Tombol Detail di Kolom 6
            container_detail = self.table.cellWidget(i, 6)
            if container_detail:
                btn_actual_detail = container_detail.findChild(QPushButton)
                if btn_actual_detail:
                    self.style_action_button(btn_actual_detail, is_large, font_table, is_delete=False)
            
            # Tombol Hapus di Kolom 7
            container_hapus = self.table.cellWidget(i, 7)
            if container_hapus:
                btn_actual_hapus = container_hapus.findChild(QPushButton)
                if btn_actual_hapus:
                    self.style_action_button(btn_actual_hapus, is_large, font_table, is_delete=True)

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

    def style_action_button(self, button, is_large, font_size, is_delete=False):
        btn_width = 130 if is_large else 105
        btn_height = 38 if is_large else 32  
        button.setFixedSize(btn_width, btn_height)
        
        bg_color = "#dc2626" if is_delete else "#0284c7"
        bg_hover = "#b91c1c" if is_delete else "#0369a1"
        bg_pressed = "#991b1b" if is_delete else "#075985"
            
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color}; 
                color: white; 
                border-radius: 6px; 
                font-weight: 700; 
                font-size: {font_size};
                border: none;
            }}
            QPushButton:hover {{ background-color: {bg_hover}; }}
            QPushButton:pressed {{ background-color: {bg_pressed}; }}
        """)

    def load_patient_data(self):
        """Mengambil data dari DBManager dan memetakan ke tabel UI dengan presisi"""
        self.table.setRowCount(0)
        patients = self.db_manager.get_all_subjects()
        
        if not patients:
            return

        self.table.setRowCount(len(patients))
        
        row_height = 65 if self.current_is_large else 52
        font_table = "11pt" if self.current_is_large else "10pt"
        
        for row_idx, patient in enumerate(patients):
            # TANGKAP 7 VAR KANONIKAL DARI DB:
            # 0:id, 1:nama, 2:umur, 3:alamat, 4:email, 5:jenis_kelamin, 6:created_at
            sub_id = patient[0]
            nama = patient[1] if len(patient) > 1 and patient[1] else "-"
            umur = patient[2] if len(patient) > 2 and patient[2] is not None else "-"
            alamat = patient[3] if len(patient) > 3 and patient[3] else "-"
            email = patient[4] if len(patient) > 4 and patient[4] else "-"
            jk = patient[5] if len(patient) > 5 and patient[5] else "-"
            tanggal = patient[6] if len(patient) > 6 and patient[6] else "-"

            patient_dict = {
                "id": sub_id,
                "nama": nama,
                "email": email,
                "umur": umur,
                "jenis_kelamin": jk,
                "alamat": alamat
            }

            self.table.setRowHeight(row_idx, row_height)

            # Buat Item Sel
            item_id = QTableWidgetItem(f"{sub_id}")
            item_nama = QTableWidgetItem(str(nama))
            item_umur = QTableWidgetItem(f"{umur} Tahun" if umur != "-" else "-")
            item_jk = QTableWidgetItem(str(jk))
            item_email = QTableWidgetItem(str(email))
            item_tanggal = QTableWidgetItem(str(tanggal))

            # Set Rata Tengah
            for item in [item_id, item_nama, item_umur, item_jk, item_email, item_tanggal]:
                item.setTextAlignment(Qt.AlignCenter)

            # MASUKKAN TEPAT KE INDEKS KOLOM UI:
            # 0: ID | 1: Nama Pasien | 2: Umur | 3: Jenis Kelamin | 4: Email | 5: Tanggal Input
            self.table.setItem(row_idx, 0, item_id)
            self.table.setItem(row_idx, 1, item_nama)
            self.table.setItem(row_idx, 2, item_umur)
            self.table.setItem(row_idx, 3, item_jk)
            self.table.setItem(row_idx, 4, item_email)
            self.table.setItem(row_idx, 5, item_tanggal)

            # Tombol Detail (Kolom 6)
            btn_test = QPushButton("Detail")  
            btn_test.setCursor(Qt.PointingHandCursor)
            self.style_action_button(btn_test, self.current_is_large, font_table, is_delete=False)
            btn_test.clicked.connect(lambda checked, p=patient_dict: self.buka_popup_detail(p))
            
            container_detail = QWidget()
            layout_detail = QHBoxLayout(container_detail)
            layout_detail.addWidget(btn_test)
            layout_detail.setContentsMargins(0, 0, 0, 0)
            layout_detail.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row_idx, 6, container_detail)

            # Tombol Hapus (Kolom 7)
            btn_hapus_row = QPushButton("Hapus")
            btn_hapus_row.setCursor(Qt.PointingHandCursor)
            self.style_action_button(btn_hapus_row, self.current_is_large, font_table, is_delete=True)
            btn_hapus_row.clicked.connect(lambda checked, sid=sub_id, name=nama: self.proses_hapus_cepat_tabel(sid, name))
            
            container_hapus = QWidget()
            layout_hapus = QHBoxLayout(container_hapus)
            layout_hapus.addWidget(btn_hapus_row)
            layout_hapus.setContentsMargins(0, 0, 0, 0)
            layout_hapus.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row_idx, 7, container_hapus)

    def proses_hapus_cepat_tabel(self, subjek_id, nama_pasien):
        """Fungsi konfirmasi hapus rekaman langsung dari baris tabel."""
        tanya = QMessageBox.question(
            self, 
            "Konfirmasi Hapus", 
            f"Apakah Anda yakin ingin menghapus permanen seluruh data rekaman milik {nama_pasien.upper()} (ID: #{subjek_id}) dari database?", 
            QMessageBox.Yes | QMessageBox.No
        )
        if tanya == QMessageBox.Yes:
            self.db_manager.hapus_rekaman_subjek(subjek_id)
            self.load_patient_data()  
            QMessageBox.information(self, "Terhapus", f"Data rekaman {nama_pasien} berhasil dihapus.")

    # ================= FUNGSI POP-UP DETAIL MODAL =================
    def buka_popup_detail(self, patient_data):
        """Membuka Jendela Pop-up Modal responsif dengan penanganan NoneType secara aman."""
        subjek_id = patient_data['id']
        
        res = self.db_manager.ambil_screenshot_terakhir(subjek_id)
        if not res or res[0] is None:
            QMessageBox.warning(self, "Data Kosong", f"Rekaman grafik untuk {patient_data['nama'].upper()} belum pernah disimpan / tidak ditemukan.")
            return

        blob_gambar, teks_analisis_saved = res

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Rekaman Medis - {patient_data['nama'].upper()}")
        dialog.setStyleSheet("background-color: #f8fafc;")
        
        parent_widget = self.window()
        parent_width, parent_height = parent_widget.width(), parent_widget.height()
        
        if self.current_is_large:
            lebar_dialog = int(parent_width * 0.70)
            tinggi_dialog = int(parent_height * 0.85)
        else:
            lebar_dialog = int(parent_width * 0.85)
            tinggi_dialog = int(parent_height * 0.88)
            
        dialog.resize(lebar_dialog, tinggi_dialog)
        dialog.setMinimumSize(700, 600)
        
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(20, 15, 20, 15)
        dialog_layout.setSpacing(10)

        # Header Biodata Pasien
        font_header = "12pt" if self.current_is_large else "10pt"
        email_str = patient_data.get('email', '-')
        lbl_info = QLabel(f"Nama: {patient_data['nama']}  |  Gender: {patient_data['jenis_kelamin']}  |  Email: {email_str}  |  Umur: {patient_data['umur']} Tahun")
        lbl_info.setStyleSheet(f"font-weight: bold; font-size: {font_header}; color: #1e293b;")
        dialog_layout.addWidget(lbl_info)

        # 1. TAMPILAN SCREENSHOT GRAFIK
        lbl_foto = QLabel()
        lbl_foto.setStyleSheet("border: 1px solid #cbd5e1; background-color: white; border-radius: 4px;")
        lbl_foto.setAlignment(Qt.AlignCenter)
        lbl_foto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        img = QImage.fromData(blob_gambar)
        pixmap = QPixmap.fromImage(img)
        
        lebar_foto_dinamis = lebar_dialog - 40
        tinggi_foto_dinamis = tinggi_dialog - 330
        lbl_foto.setPixmap(pixmap.scaled(lebar_foto_dinamis, tinggi_foto_dinamis, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        dialog_layout.addWidget(lbl_foto)

        # 2. AREA LAPORAN TEKS ANALISIS
        lbl_judul_analisis = QLabel("Hasil Analisis & Kesimpulan Subjek (Automated Expert System):")
        lbl_judul_analisis.setStyleSheet("font-weight: bold; color: #475569; margin-top: 5px;")
        dialog_layout.addWidget(lbl_judul_analisis)

        teks_deskripsi_eeg = (
            "Electroencephalogram (EEG) merupakan salah satu teknik non-invasif, berfungsi untuk "
            "merekam aktivitas listrik otak melalui elektroda yang diletakkan di permukaan kulit kepala manusia.\n\n"
        )
        
        teks_lengkap_pop_up = teks_deskripsi_eeg + (teks_analisis_saved if teks_analisis_saved else "Data kesimpulan klinis kosong.")

        self.txt_analisis = QTextEdit()
        self.txt_analisis.setFixedHeight(180)
        self.txt_analisis.setReadOnly(True)
        self.txt_analisis.setStyleSheet("""
            QTextEdit {
                background-color: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 10px;
                font-family: 'Segoe UI', Arial;
                font-size: 9.5pt;
                line-height: 140%;
                color: #334155;
            }
        """)
        self.txt_analisis.setText(teks_lengkap_pop_up)
        dialog_layout.addWidget(self.txt_analisis)

        # 3. BARIS TOMBOL AKSI BAWAH
        aksi_layout = QHBoxLayout()
        font_btn = "11pt" if self.current_is_large else "9.5pt"
        btn_padding = "10px 20px" if self.current_is_large else "6px 14px"
        btn_style_base = f"font-weight: bold; padding: {btn_padding}; font-size: {font_btn}; border-radius: 5px; border: none;"
        
        btn_pdf = QPushButton("📥 Unduh PDF Report")
        btn_pdf.setCursor(Qt.PointingHandCursor)
        btn_pdf.setStyleSheet(f"background-color: #16a34a; color: white; {btn_style_base}")
        
        btn_hapus = QPushButton("🗑️ Hapus Rekaman")
        btn_hapus.setCursor(Qt.PointingHandCursor)
        btn_hapus.setStyleSheet(f"background-color: #dc2626; color: white; {btn_style_base}")
        
        btn_tutup = QPushButton("Tutup")
        btn_tutup.setCursor(Qt.PointingHandCursor)
        btn_tutup.setStyleSheet(f"background-color: #64748b; color: white; {btn_style_base}")
        
        aksi_layout.addWidget(btn_pdf)
        aksi_layout.addWidget(btn_hapus)
        aksi_layout.addStretch()
        aksi_layout.addWidget(btn_tutup)
        dialog_layout.addLayout(aksi_layout)

        # --- FUNGSI EKSPOR PDF ---
        def proses_unduh_pdf():
            teks_paragraf = self.txt_analisis.toPlainText().strip()
            path_simpan, _ = QFileDialog.getSaveFileName(self, "Simpan Laporan PDF", f"Laporan_EEG_{patient_data['nama']}.pdf", "PDF Files (*.pdf)")
            if path_simpan:
                try:
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    
                    cache_img_path = "temp_eeg_report.png"
                    with open(cache_img_path, "wb") as f:
                        f.write(blob_gambar)
                        
                    doc = SimpleDocTemplate(path_simpan, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottom=40)
                    story = []
                    styles = getSampleStyleSheet()
                    
                    style_judul = ParagraphStyle('JudulLaporan', parent=styles['Heading1'], fontSize=18, leading=22, textColor='#0284c7', alignment=1, spaceAfter=15)
                    story.append(Paragraph("LAPORAN RESMI MONITORING SIGNAL EEG", style_judul))
                    story.append(Spacer(1, 10))
                    
                    meta_text = f"<b>ID Pasien:</b> #{patient_data['id']}<br/><b>Nama Pasien:</b> {patient_data['nama']}<br/><b>Email:</b> {patient_data.get('email', '-')}<br/><b>Umur / Gender:</b> {patient_data['umur']} Tahun / {patient_data['jenis_kelamin']}<br/>"
                    story.append(Paragraph(meta_text, styles['Normal']))
                    story.append(Spacer(1, 10))
                    
                    story.append(Paragraph("<b>Visualisasi Gelombang Otak Real-time Terakhir:</b>", styles['Normal']))
                    story.append(Spacer(1, 5))
                    story.append(Image(cache_img_path, width=520, height=270))
                    story.append(Spacer(1, 12))
                    
                    teks_pdf_formatted = teks_paragraf.replace('\n', '<br/>')
                    style_analisis_pdf = ParagraphStyle(
                        'AnalisisKlinisText',
                        parent=styles['Normal'],
                        fontSize=9.5,
                        leading=13.5,
                        alignment=4,
                        textColor='#1e293b'
                    )
                    story.append(Paragraph(teks_pdf_formatted, style_analisis_pdf))
                    
                    doc.build(story)
                    if os.path.exists(cache_img_path):
                        os.remove(cache_img_path)
                        
                    QMessageBox.information(dialog, "Sukses", "Laporan PDF Lengkap Berhasil Diunduh!")
                except Exception as ex:
                    QMessageBox.critical(dialog, "Gagal PDF", f"Terjadi kesalahan saat mengekspor PDF: {ex}")

        def proses_hapus_data():
            tanya = QMessageBox.question(dialog, "Konfirmasi Hapus", f"Apakah Anda yakin ingin menghapus permanen data rekaman {patient_data['nama']} dari database?", QMessageBox.Yes | QMessageBox.No)
            if tanya == QMessageBox.Yes:
                self.db_manager.hapus_rekaman_subjek(subjek_id)
                self.load_patient_data()  
                dialog.accept()           
                QMessageBox.information(self, "Terhapus", "Data rekaman subjek berhasil dibersihkan dari database.")

        btn_pdf.clicked.connect(proses_unduh_pdf)
        btn_hapus.clicked.connect(proses_hapus_data)
        btn_tutup.clicked.connect(dialog.accept)

        dialog.exec_()