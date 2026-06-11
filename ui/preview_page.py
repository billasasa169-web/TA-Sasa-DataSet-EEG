from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class PreviewPage(QWidget):
    def __init__(self, on_start_test_callback):
        super().__init__()
        self.on_start_test_callback = on_start_test_callback
        self.current_data = None
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setAlignment(Qt.AlignTop)

        self.title = QLabel("PRATINJAU DATA SUBJEK")
        self.title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #333;")
        self.layout.addWidget(self.title)

        self.card = QFrame()
        self.card.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 8px;")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(30, 30, 30, 30)

        self.info_labels = QLabel("Tidak ada data pasien yang dimuat.")
        self.info_labels.setStyleSheet("font-size: 12pt; line-height: 20px; border:none;")
        self.card_layout.addWidget(self.info_labels)
        self.layout.addWidget(self.card)

        # Kontrol Navigasi
        actions_layout = QHBoxLayout()
        self.pdf_btn = QPushButton("Ekspor PDF Kartu")
        self.pdf_btn.clicked.connect(self.export_pdf)
        self.pdf_btn.setStyleSheet("background-color: #e74c3c; color: white; padding: 10px 20px; font-weight:bold; border-radius:4px;")
        
        self.test_btn = QPushButton("Lanjut Ke Ruang Pengujian Sinyal ➔")
        self.test_btn.clicked.connect(lambda: self.on_start_test_callback(self.current_data))
        self.test_btn.setStyleSheet("background-color: #2ecc71; color: white; padding: 10px 20px; font-weight:bold; border-radius:4px;")

        actions_layout.addWidget(self.pdf_btn)
        actions_layout.addStretch()
        actions_layout.addWidget(self.test_btn)
        self.layout.addLayout(actions_layout)

    def set_subjek_data(self, data):
        self.current_data = data
        text = f"<b>ID Rekam Medis:</b> #{data['id']}<br><br>" \
               f"<b>Nama Lengkap:</b> {data['nama']}<br><br>" \
               f"<b>Umur Pasien:</b> {data['umur']} Tahun<br><br>" \
               f"<b>Alamat Tinggal:</b> {data['alamat']}<br><br>" \
               f"<b>Kontak Email:</b> {data['email']}<br><br>" \
               f"<b>Jenis Kelamin:</b> {data['jenis_kelamin']}"
        self.info_labels.setText(text)

    def export_pdf(self):
        if not self.current_data: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Simpan Rekam Pasien", f"Pasien_{self.current_data['nama']}.pdf", "PDF Files (*.pdf)")
        if file_path:
            c = canvas.Canvas(file_path, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, h - 60, "KARTU IDENTITAS SUBJEK UJI EEG")
            c.setStrokeColorRGB(0.2, 0.2, 0.2)
            c.line(50, h - 75, w - 50, h - 75)
            
            c.setFont("Helvetica", 12)
            y = h - 120
            for k, v in self.current_data.items():
                c.drawString(60, y, f"{k.upper().replace('_', ' ')} :")
                c.drawString(200, y, str(v))
                y -= 25
            c.save()
            QMessageBox.information(self, "Sukses", "Berkas PDF Subjek Berhasil Terbit!")