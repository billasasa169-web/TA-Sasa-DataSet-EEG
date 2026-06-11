# ui/main_window.py

import os
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QFrame, QPushButton, QStackedWidget, QLabel, QMessageBox)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QIcon # Diperlukan untuk merender file gambar ikon
from ui.form_page import FormPage
from ui.monitor_page import MonitorPage
from ui.history_page import HistoryPage

class MainWindow(QMainWindow):
    def __init__(self, db_manager, ble_worker):
        super().__init__()
        self.db_manager = db_manager
        self.ble_worker = ble_worker
        self.is_subject_ready = False 
        
        # 1. Konfigurasi Path Folder Assets secara Absolut (Root Project)
        # __file__ ada di root/ui/main_window.py, mundur 1 langkah ke root proyek
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.assets_dir = os.path.join(base_dir, "assets")
        
        # Menyimpan nilai default untuk ukuran normal (Resolusi Kecil)
        self.sidebar_normal_width = 400
        self.sidebar_large_width = 480
        self.current_sidebar_target = self.sidebar_normal_width
        
        self.setWindowTitle("Sistem Pemantauan EEG Nirkabel")
        self.resize(1300, 800)
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.main_layout = QHBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ================= SIDEBAR KIRI =================
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(self.sidebar_normal_width)
        self.sidebar.setMinimumWidth(0) 
        self.sidebar.setStyleSheet("background-color: #1e293b; border-right: 1px solid #0f172a;")
        
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(24, 30, 24, 24)
        self.sidebar_layout.setSpacing(18)
        
        # Header Brand & Tombol Close
        brand_layout = QHBoxLayout()
        
        # Label Logo Brand Utama (Jika Anda punya file logo, bisa dimasukkan ke sini)
        self.brand_title = QLabel("EEG APP SYSTEM")
        
        self.btn_close_sidebar = QPushButton("◀")
        self.btn_close_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_close_sidebar.clicked.connect(self.toggle_sidebar)
        
        brand_layout.addWidget(self.brand_title)
        brand_layout.addWidget(self.btn_close_sidebar)
        self.sidebar_layout.addLayout(brand_layout)
        
        self.sidebar_layout.addSpacing(25)

        # Navigasi Button Menu - Emoticon teks dihapus, diganti spasi penampung QIcon
        self.btn_form = QPushButton("   Data Subjek")
        self.btn_monitor = QPushButton("   Rekaman Baru")
        self.btn_history = QPushButton("   Riwayat Rekaman")
        

        # Load file gambar dari folder assets ke objek QIcon
        self.icon_form = QIcon(os.path.join(self.assets_dir, "input.png"))
        self.icon_monitor = QIcon(os.path.join(self.assets_dir, "monitor.png"))
        self.icon_history = QIcon(os.path.join(self.assets_dir, "riwayat.png"))
        
        # Tempelkan QIcon ke masing-masing tombol fisik
        self.btn_form.setIcon(self.icon_form)
        self.btn_history.setIcon(self.icon_history)
        self.btn_monitor.setIcon(self.icon_monitor)

        self.buttons = [self.btn_form, self.btn_monitor, self.btn_history]
        for btn in self.buttons:
            btn.setCheckable(True)
            self.sidebar_layout.addWidget(btn)
            
        self.btn_monitor.setEnabled(False)
        self.sidebar_layout.addStretch()
        
        # Footer Teks
        self.footer_label = QLabel("v0.0.1 Bachelor Thesis")
        self.sidebar_layout.addWidget(self.footer_label)
        
        self.main_layout.addWidget(self.sidebar)

        # ================= AREA KONTEN UTAMA KANAN =================
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # TOP BAR PANEL
        self.top_bar = QFrame()
        self.top_bar.setStyleSheet("background-color: white; border-bottom: 1px solid #e2e8f0;")
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(16, 0, 16, 0)
        
        self.btn_hamburger = QPushButton("☰")
        self.btn_hamburger.setCursor(Qt.PointingHandCursor)
        self.btn_hamburger.setVisible(False) 
        self.btn_hamburger.clicked.connect(self.toggle_sidebar)
        
        self.session_title = QLabel("Comport Panel | Wireless EEG Monitoring Terminal")
        
        top_bar_layout.addWidget(self.btn_hamburger)
        top_bar_layout.addWidget(self.session_title)
        top_bar_layout.addStretch()
        
        right_layout.addWidget(self.top_bar)

        # AREA STACKED CONTAINER HALAMAN
        self.pages_container = QStackedWidget()
        
        self.page_form = FormPage(self.db_manager, self.handle_form_submitted)
        self.page_monitor = MonitorPage(self.ble_worker)      
        self.page_history = HistoryPage(self.db_manager, self.handle_history_patient_selected) 

        self.pages_container.addWidget(self.page_form)        # Indeks 0
        self.pages_container.addWidget(self.page_monitor)     # Indeks 1
        self.pages_container.addWidget(self.page_history)     # Indeks 2
        
        right_layout.addWidget(self.pages_container, 1)
        self.main_layout.addWidget(right_container, 1)

        self.btn_form.clicked.connect(lambda: self.switch_page(0))
        self.btn_monitor.clicked.connect(lambda: self.switch_page(1))
        self.btn_history.clicked.connect(lambda: self.switch_page(2))
        
        self.switch_page(0)

    def resizeEvent(self, event):
        """Mekanisme Media Query Dinamis - Mendeteksi Perubahan Ukuran Window"""
        current_width = event.size().width()
        if current_width >= 1600:
            self.apply_media_query_styles(is_large=True)
        else:
            self.apply_media_query_styles(is_large=False)
        super().resizeEvent(event)

    def apply_media_query_styles(self, is_large):
        """Mengubah Ukuran Font, Padding, Dimensi Komponen, dan Ukuran Ikon Secara Real-time"""
        if is_large:
            font_base = "12pt"
            font_title = "15pt"
            font_btn = "13pt"
            btn_height = 80
            top_bar_height = 80
            hamburger_size = 46
            close_btn_size = 38
            icon_size = QSize(32, 32) # Ikon membesar di layar resolusi tinggi
            
            self.current_sidebar_target = self.sidebar_large_width
            if self.sidebar.width() > 0:
                self.sidebar.setFixedWidth(self.sidebar_large_width)
        else:
            font_base = "10pt"
            font_title = "12pt"
            font_btn = "10.5pt"
            btn_height = 65
            top_bar_height = 60
            hamburger_size = 36
            close_btn_size = 32
            icon_size = QSize(24, 24) # Ikon berukuran standar di resolusi normal
            
            self.current_sidebar_target = self.sidebar_normal_width
            if self.sidebar.width() > 0:
                self.sidebar.setFixedWidth(self.sidebar_normal_width)

        # Amandemen dimensi widget kontroler
        self.top_bar.setFixedHeight(top_bar_height)
        self.btn_hamburger.setFixedSize(hamburger_size, hamburger_size)
        self.btn_close_sidebar.setFixedSize(close_btn_size, close_btn_size)

        # Update Style Medis QSS Kurung Kurawal Ganda
        self.setStyleSheet(f"QWidget {{ font-family: 'Segoe UI', Arial; font-size: {font_base}; color: #2c3e50; }} QMainWindow {{ background-color: #f8f9fa; }}")
        self.brand_title.setStyleSheet(f"color: #f8fafc; font-size: {font_title}; font-weight: 800; letter-spacing: 1px;")
        self.session_title.setStyleSheet(f"font-size: {font_btn}; font-weight: 700; color: #475569; margin-left: 10px;")
        
        self.btn_close_sidebar.setStyleSheet(f"QPushButton {{ background-color: #334155; color: #94a3b8; border: none; border-radius: 6px; font-size: {font_base}; font-weight: bold; }} QPushButton:hover {{ background-color: #ef4444; color: white; }}")
        self.btn_hamburger.setStyleSheet(f"QPushButton {{ background-color: #f1f5f9; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 8px; font-size: {font_title}; font-weight: bold; }} QPushButton:hover {{ background-color: #e2e8f0; }}")

        # Update Ukuran Tombol Navigasi Menu Sidebar dan Ukuran Ikon Dinamisnya
        for btn in self.buttons:
            btn.setMinimumHeight(btn_height)
            btn.setIconSize(icon_size) 
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: #94a3b8; 
                    background-color: transparent; 
                    text-align: left; 
                    
                    /* Kunci Rata Tengah Vertikal */
                    padding-top: 0px;
                    padding-bottom: 0px;
                    
                    /* Jarak Aman dari Dinding Kiri */
                    padding-left: 33px; 
                    
                    border: none; 
                    font-size: {font_btn}; 
                    font-weight: 600; 
                    border-radius: 8px;
                }}
                QPushButton:hover {{ color: #f8fafc; background-color: #334155; }}
                QPushButton:checked {{ color: white; background-color: #0284c7; }}
                QPushButton:disabled {{ color: #475569; background-color: transparent; }}
            """)
            
        self.footer_label.setStyleSheet(f"color: #475569; font-size: calc({font_base} - 2pt); font-weight: 500; padding-left: 16px;")

    def toggle_sidebar(self):
        current_width = self.sidebar.width()
        if current_width > 0:
            target_width = 0
            self.btn_hamburger.setVisible(True)
        else:
            target_width = self.current_sidebar_target
            self.btn_hamburger.setVisible(False)

        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(250) 
        self.animation.setStartValue(current_width)
        self.animation.setEndValue(target_width)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.animation.valueChanged.connect(lambda val: self.sidebar.setMaximumWidth(val))
        self.animation.start()

    def switch_page(self, index):
        if index == 1 and not self.is_subject_ready:
            QMessageBox.warning(self, "Akses Terkunci", "Instrumen monitoring steril. Sesi hanya dapat diakses via registrasi pasien baru atau basis data historis.")
            self.btn_form.setChecked(True)
            return

        self.pages_container.setCurrentIndex(index)
        for i, btn in enumerate(self.buttons):
            btn.setChecked(i == index)

        if index == 2:
            self.page_history.load_patient_data()

    def handle_form_submitted(self, data):
        self.is_subject_ready = True       
        self.btn_monitor.setEnabled(True)  
        self.page_monitor.start_test(data)
        self.switch_page(1)

    def handle_history_patient_selected(self, data):
        self.is_subject_ready = True
        self.btn_monitor.setEnabled(True)
        self.page_monitor.start_test(data)
        self.switch_page(1)

    def closeEvent(self, event):
        self.page_monitor.stop_stream()
        super().closeEvent(event)