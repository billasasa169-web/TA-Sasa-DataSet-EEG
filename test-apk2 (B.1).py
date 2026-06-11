# Script utama untuk aplikasi 

import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy,
    QStackedWidget, QFileDialog, QFormLayout, QTabWidget, QGridLayout,
    QStyle, QRadioButton, QButtonGroup
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter, QPolygon, QPen,
    QBrush
)
from PyQt5.QtCore import Qt, QSize, QUrl, QPoint
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
import math # Import math for font size calculation
import urllib.request # Import for downloading images
import random # For generating placeholder data

class EEGMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Pemantauan EEG Nirkabel")
        # Mengatur ukuran awal tanpa mengunci ukuran jendela
        self.resize(1000, 600)

        # Colors
        self.primary_color = "#056fd9"  # Dark blue for header
        self.secondary_color = "#ecf0f1" # Light gray for background
        self.accent_color = "#3498db"    # Blue for buttons/highlights
        self.text_color = "#333333"      # Dark text
        self.entry_bg = "#f0f8ff"        # Light blue for entry fields

        self.current_preview_data = {}

        self._apply_global_styles()
        self._init_ui()
        
        # Panggil pembaruan font setelah semua UI dibuat untuk mencegah AttributeError
        self._update_responsive_fonts()


    def _apply_global_styles(self):
        # Apply global stylesheet for consistent look
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.secondary_color};
            }}
            QLabel {{
                color: {self.text_color};
            }}
            QLineEdit {{
                background-color: {self.entry_bg};
                border: 1px solid #ccc;
                padding: 5px;
                font-size: 12pt;
                color: {self.text_color};
            }}
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 8px 15px;
                font-weight: bold;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: #2980b9;
            }}
            QFrame#HeaderFrame {{
                background-color: {self.primary_color};
            }}
            QFrame#SidebarFrame {{
                background-color: white;
                border: 1px solid #ddd;
            }}
            QFrame#ContentFrame, QFrame#PreviewFrame {{
                background-color: {self.secondary_color};
            }}
            .SidebarButtonFrame {{
                background-color: white;
            }}
            .SidebarButtonFrame:hover {{
                background-color: {self.accent_color};
            }}
            .SidebarButton {{
                background-color: white;
                color: {self.text_color};
                border: none;
                text-align: left;
                padding: 8px 0px;
                font-size: 12pt;
            }}
            .SidebarButton:hover {{
                background-color: {self.accent_color};
                color: white;
            }}
            .SidebarIcon {{
                background-color: white;
                font-size: 28pt;
                padding: 5px 0px;
            }}
            .SidebarIcon:hover {{
                background-color: {self.accent_color};
                color: white;
            }}
            /* Style for the Rekaman Baru page */
            QFrame#GraphContainer {{
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }}
            QFrame#GraphPanel {{
                background-color: #ecf0f1;
            }}
            QFrame#TopBar {{
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
            }}
            /* Style for the manual tabs */
            #TabButton {{
                background-color: #f0f0f0;
                color: #555;
                border: 1px solid #ccc;
                border-bottom: none;
                border-radius: 5px 5px 0 0;
                padding: 6px 12px;
                margin-right: 1px;
            }}
            #TabButton:checked {{
                background-color: white;
                color: {self.text_color};
                border: 1px solid #ccc;
                border-bottom: 1px solid white;
            }}
            #ControlButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                padding: 6px 12px;
                font-weight: bold;
                border-radius: 5px;
            }}
            #ControlLabel {{
                color: #555;
            }}
        """)

    def _init_ui(self):
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header Frame
        self.header_frame = QFrame(self.central_widget)
        self.header_frame.setObjectName("HeaderFrame")
        self.header_frame.setFixedHeight(80)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setAlignment(Qt.AlignCenter)
        self.header_label = QLabel("Sistem Pemantauan EEG Nirkabel", self.header_frame)
        self.header_label.setStyleSheet("color: white; background-color: transparent;")
        self.header_layout.addWidget(self.header_label)
        self.main_layout.addWidget(self.header_frame)

        # Content Area
        self.content_area = QWidget(self.central_widget)
        self.content_layout = QHBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_area, 1)

        # Sidebar Frame - Use size policy instead of fixed width
        self.sidebar_frame = QFrame(self.content_area)
        self.sidebar_frame.setObjectName("SidebarFrame")
        self.sidebar_frame.setFixedWidth(250)
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(0, 20, 0, 20)
        self.sidebar_layout.setSpacing(2)

        self.features_label = QLabel("Fitur Utama", self.sidebar_frame)
        self.features_label.setAlignment(Qt.AlignLeft)
        self.features_label.setStyleSheet("padding-left: 15px; background-color: transparent;")
        self.sidebar_layout.addWidget(self.features_label)
        self.sidebar_layout.addSpacing(10)

        # URLs for the icons - you can replace these with your own
        self.icon_urls = {
            "Data Subjek": "https://img.icons8.com/plasticine/100/gender-neutral-user.png",
            "Rekaman Baru": "https://img.icons8.com/plasticine/100/edit-file.png",
            "Riwayat Rekaman": "https://img.icons8.com/plasticine/100/time-machine--v2.png"
        }

        self.data_subjek_btn = self._create_sidebar_button("Data Subjek", self.icon_urls["Data Subjek"], self.show_data_subjek_form)
        self.rekaman_baru_btn = self._create_sidebar_button("Rekaman Baru", self.icon_urls["Rekaman Baru"], self.show_rekaman_baru)
        self.riwayat_rekaman_btn = self._create_sidebar_button("Riwayat Rekaman", self.icon_urls["Riwayat Rekaman"], self.show_riwayat_rekaman)

        self.sidebar_layout.addWidget(self.data_subjek_btn)
        self.sidebar_layout.addWidget(self.rekaman_baru_btn)
        self.sidebar_layout.addWidget(self.riwayat_rekaman_btn)
        self.sidebar_layout.addStretch()

        self.content_layout.addWidget(self.sidebar_frame)

        # Stacked Widget for Main Content Pages
        self.stacked_widget = QStackedWidget(self.content_area)
        self.content_layout.addWidget(self.stacked_widget)

        # Pages
        self._create_data_subjek_form_page()
        self._create_data_preview_page()
        self._create_rekaman_baru_page()
        self._create_riwayat_rekaman_page()

        # Footer
        self.footer_frame = QFrame(self.central_widget)
        self.footer_frame.setStyleSheet(f"background-color: {self.secondary_color};")
        self.footer_frame.setFixedHeight (50)
        self.footer_layout = QHBoxLayout(self.footer_frame)
        self.footer_layout.setContentsMargins(20, 10, 20, 10)
        self.footer_layout.setAlignment(Qt.AlignVCenter)

        self.left_arrow = QLabel("⏪", self.footer_frame)
        self.left_arrow.setStyleSheet(f"color: {self.accent_color}; background-color: transparent;")
        self.footer_layout.addWidget(self.left_arrow)

        self.info_label = QLabel("Pastikan semua data pasien diisi dengan lengkap dan benar !", self.footer_frame)
        self.info_label.setStyleSheet(f"color: {self.text_color}; background-color: transparent;")
        self.info_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.info_label.setWordWrap(True)
        self.footer_layout.addWidget(self.info_label, 1)

        self.right_arrow = QLabel("⏩", self.footer_frame)
        self.right_arrow.setStyleSheet(f"color: {self.accent_color}; background-color: transparent;")
        self.footer_layout.addWidget(self.right_arrow)
        self.main_layout.addWidget(self.footer_frame)

        # Initial view
        self.show_data_subjek_form()

    def _create_sidebar_button(self, text, image_url, command):
        btn_container = QFrame()
        btn_container.setObjectName("SidebarButtonFrame")
        btn_container_layout = QHBoxLayout(btn_container)
        btn_container_layout.setContentsMargins(0, 0, 0, 0)
        btn_container_layout.setSpacing(0)

        # Load image from URL
        try:
            image_data = urllib.request.urlopen(image_url).read()
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
        except urllib.error.URLError:
            print(f"Failed to load image from {image_url}. Using placeholder.")
            pixmap = QPixmap(QSize(55, 55))
            pixmap.fill(Qt.lightGray)

        # Scale the pixmap to the desired size
        icon_label = QLabel()
        icon_label.setPixmap(pixmap.scaled(QSize(40, 40), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setStyleSheet("padding-left: 15px; background-color: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        btn_container_layout.addWidget(icon_label)

        button = QPushButton(text)
        button.setObjectName("SidebarButton")
        button.setCursor(Qt.PointingHandCursor)
        button.clicked.connect(command)
        btn_container_layout.addWidget(button, 1)

        return btn_container

    def _create_data_subjek_form_page(self):
        self.data_subjek_form_page = QWidget()
        self.data_subjek_form_page.setObjectName("ContentFrame")
        form_layout = QVBoxLayout(self.data_subjek_form_page)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setAlignment(Qt.AlignTop)

        self.form_title = QLabel("SUBJEK")
        self.form_title.setStyleSheet("margin-bottom: 20px; background-color: transparent;")
        form_layout.addWidget(self.form_title)

        form_main_layout = QHBoxLayout()
        form_layout.addLayout(form_main_layout)

        form_main_layout.addStretch() 
        
        # Menggunakan QFormLayout untuk tata letak label dan input yang lebih baik
        form_grid_layout = QFormLayout()
        form_grid_layout.setContentsMargins(0, 0, 0, 0)
        form_grid_layout.setHorizontalSpacing(10)
        form_grid_layout.setVerticalSpacing(10)
        form_main_layout.addLayout(form_grid_layout)

        labels = ["Nama", "Umur", "Alamat", "Email"]
        self.entries = {}
        self.form_labels = {}
        
        for label_text in labels:
            label = QLabel(label_text)
            self.form_labels[label_text] = label
            
            entry = QLineEdit()
            entry.setPlaceholderText(f"Masukkan {label_text.lower()}")
            entry.setMinimumWidth(300)
            entry.setMinimumHeight(35)
            self.entries[label_text] = entry
            
            form_grid_layout.addRow(label, entry)
        
                # ==== Jenis Kelamin (Radio Button) ====
        jk_label = QLabel("Jenis Kelamin")
        self.form_labels["Jenis Kelamin"] = jk_label
        self.laki_radio = QRadioButton("Laki-laki")
        self.perempuan_radio = QRadioButton("Perempuan")

        # Supaya hanya bisa pilih satu
        self.jk_group = QButtonGroup()
        self.jk_group.addButton(self.laki_radio)
        self.jk_group.addButton(self.perempuan_radio)

        jk_layout = QHBoxLayout()
        jk_layout.addWidget(self.laki_radio)
        jk_layout.addWidget(self.perempuan_radio)

        form_grid_layout.addRow(jk_label, jk_layout)


        form_main_layout.addStretch()

        self.add_data_btn = QPushButton("Tambah Data")
        self.add_data_btn.setMinimumSize(150, 40)
        self.add_data_btn.setMaximumWidth(200)
        self.add_data_btn.clicked.connect(self.add_data)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.add_data_btn)
        form_layout.addLayout(button_layout)

        form_layout.addStretch()

        self.stacked_widget.addWidget(self.data_subjek_form_page)

    def _create_data_preview_page(self):
        self.data_preview_page = QWidget()
        self.data_preview_page.setObjectName("PreviewFrame")
        self.preview_layout = QVBoxLayout(self.data_preview_page)
        self.preview_layout.setContentsMargins(20, 20, 20, 20)
        self.preview_layout.setAlignment(Qt.AlignTop)

        self.preview_title = QLabel("Pratinjau Data Subjek")
        self.preview_title.setStyleSheet("margin-bottom: 20px; background-color: transparent;")
        self.preview_title.setAlignment(Qt.AlignCenter)
        self.preview_layout.addWidget(self.preview_title)

        self.data_display_container = QFrame()
        self.data_display_container.setStyleSheet("background-color: white; border: 1px solid #ddd; border-radius: 5px;")
        self.data_display_layout = QVBoxLayout(self.data_display_container)
        self.data_display_layout.setContentsMargins(50, 30, 50, 30)

        self.preview_labels = {}

        self.preview_grid_layout = QVBoxLayout()
        self.data_display_layout.addLayout(self.preview_grid_layout)
        
        h_center_layout = QHBoxLayout()
        h_center_layout.addStretch()
        h_center_layout.addWidget(self.data_display_container, 3)
        h_center_layout.addStretch()
        self.preview_layout.addLayout(h_center_layout)

        button_layout = QHBoxLayout()
        self.save_pdf_btn = QPushButton("Simpan sebagai PDF")
        self.save_pdf_btn.clicked.connect(self.save_as_pdf)
        button_layout.addWidget(self.save_pdf_btn)

        self.save_png_btn = QPushButton("Simpan sebagai PNG")
        self.save_png_btn.clicked.connect(self.save_as_png)
        button_layout.addWidget(self.save_png_btn)
        
        h_center_buttons_layout = QHBoxLayout()
        h_center_buttons_layout.addStretch()
        h_center_buttons_layout.addLayout(button_layout)
        h_center_buttons_layout.addStretch()
        
        self.preview_layout.addLayout(h_center_buttons_layout)
        self.preview_layout.addStretch()

        self.stacked_widget.addWidget(self.data_preview_page)

    def _create_rekaman_baru_page(self):
        self.rekaman_baru_page = QWidget()
        self.rekaman_baru_page.setObjectName("ContentFrame")
        main_layout = QVBoxLayout(self.rekaman_baru_page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Top control bar with manual tabs and buttons
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(5, 5, 5, 5)
        top_layout.setSpacing(10)

        # Manual tabs
        self.time_series_tab_btn = QPushButton("Time Series")
        self.time_series_tab_btn.setObjectName("TabButton")
        self.time_series_tab_btn.setCheckable(True)
        self.time_series_tab_btn.setChecked(True)

        self.head_plot_tab_btn = QPushButton("Head Plot")
        self.head_plot_tab_btn.setObjectName("TabButton")
        self.head_plot_tab_btn.setCheckable(True)

        top_layout.addWidget(self.time_series_tab_btn)
        top_layout.addWidget(self.head_plot_tab_btn)
        top_layout.addStretch(1)

        # Control buttons
        top_layout.addWidget(QPushButton("Start Data Stream"))
        top_layout.addWidget(QPushButton("Save"))
        top_layout.addWidget(QPushButton("Setting"))
        top_layout.addWidget(QPushButton("Help"))

        main_layout.addWidget(top_bar)

        # Stacked widget for the content of the tabs
        self.rekaman_stacked_widget = QStackedWidget()
        
        # Create content pages for each tab
        time_series_page = self._create_time_series_page()
        head_plot_page = self._create_head_plot_page()

        self.rekaman_stacked_widget.addWidget(time_series_page)
        self.rekaman_stacked_widget.addWidget(head_plot_page)

        main_layout.addWidget(self.rekaman_stacked_widget, 1)

        # Connect button signals to the stacked widget
        self.time_series_tab_btn.clicked.connect(lambda: self.rekaman_stacked_widget.setCurrentIndex(0))
        self.head_plot_tab_btn.clicked.connect(lambda: self.rekaman_stacked_widget.setCurrentIndex(1))

        # Ensure only one tab is checked at a time
        self.time_series_tab_btn.toggled.connect(self.head_plot_tab_btn.setChecked)
        self.head_plot_tab_btn.toggled.connect(self.time_series_tab_btn.setChecked)
        
        self.stacked_widget.addWidget(self.rekaman_baru_page)

    def _create_time_series_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Graph section
        time_series_frame = QFrame()
        time_series_frame.setObjectName("GraphContainer")
        time_series_layout = QVBoxLayout(time_series_frame)
        time_series_layout.setContentsMargins(10, 10, 10, 10)
        time_series_layout.addWidget(QLabel("Time Series"))
        time_series_layout.addWidget(QLabel("Channel: 1"))
        time_series_layout.addWidget(QLabel("Time (s)"))
        time_series_layout.addWidget(QLabel("Placeholder for Time Series Graph"))
        
        layout.addWidget(time_series_frame, 0, 0, 1, 1)

        # FFT section
        fft_frame = QFrame()
        fft_frame.setObjectName("GraphContainer")
        fft_layout = QVBoxLayout(fft_frame)
        fft_layout.setContentsMargins(10, 10, 10, 10)
        fft_layout.addWidget(QLabel("FFT Plot"))
        fft_layout.addWidget(QLabel("Placeholder for FFT Graph"))

        layout.addWidget(fft_frame, 1, 0, 1, 1)
        
        return page

    def _create_head_plot_page(self):
        page = QWidget()
        layout = QGridLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Head Plot section
        head_plot_frame = QFrame()
        head_plot_frame.setObjectName("GraphContainer")
        head_plot_layout = QVBoxLayout(head_plot_frame)
        head_plot_layout.setContentsMargins(10, 10, 10, 10)
        head_plot_layout.addWidget(QLabel("Head Plot"))
        head_plot_layout.addWidget(self._create_head_plot_widget())
        
        layout.addWidget(head_plot_frame, 0, 0, 1, 1)
        
        # Radar Plot section
        radar_plot_frame = QFrame()
        radar_plot_frame.setObjectName("GraphContainer")
        radar_plot_layout = QVBoxLayout(radar_plot_frame)
        radar_plot_layout.setContentsMargins(10, 10, 10, 10)
        radar_plot_layout.addWidget(QLabel("Radar Plot"))
        radar_plot_layout.addWidget(self._create_radar_plot_widget())
        
        layout.addWidget(radar_plot_frame, 1, 0, 1, 1)

        return page

    def _create_head_plot_widget(self):
        head_widget = QWidget()
        head_layout = QVBoxLayout(head_widget)
        head_layout.setContentsMargins(0, 0, 0, 0)
        
        # Draw a simple head diagram with electrode labels
        head_diagram = QPixmap(300, 300)
        head_diagram.fill(Qt.transparent)
        
        painter = QPainter(head_diagram)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Head outline
        painter.setPen(QColor(0, 0, 0))
        painter.drawEllipse(50, 50, 200, 200)
        
        # Ear outlines
        painter.drawEllipse(20, 120, 30, 60)
        painter.drawEllipse(250, 120, 30, 60)
        
        # Nose
        painter.drawLine(150, 250, 150, 270)
        
        # Electrode positions (placeholders)
        font = painter.font()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor(0, 0, 255))
        
        # Labels for electrodes
        electrode_labels = {
            "Fp1": (100, 80), "Fp2": (200, 80),
            "C3": (100, 150), "C4": (200, 150),
            "O1": (120, 220), "O2": (180, 220),
            "P3": (100, 180), "P4": (200, 180),
            "F3": (100, 120), "F4": (200, 120)
        }
        
        for label, pos in electrode_labels.items():
            painter.drawEllipse(pos[0]-5, pos[1]-5, 10, 10)
            painter.drawText(pos[0]+10, pos[1]+5, label)
            
        painter.end()
        
        head_label = QLabel()
        head_label.setPixmap(head_diagram)
        head_layout.addWidget(head_label)
        
        return head_widget

    def _create_radar_plot_widget(self):
        radar_widget = QWidget()
        radar_layout = QVBoxLayout(radar_widget)
        radar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Draw a simple placeholder radar plot
        radar_diagram = QPixmap(300, 300)
        radar_diagram.fill(Qt.transparent)
        
        painter = QPainter(radar_diagram)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Center of the plot
        center_x, center_y = 150, 150
        
        # Draw axes
        painter.setPen(QColor(150, 150, 150))
        painter.drawLine(center_x, 50, center_x, 250)
        painter.drawLine(50, center_y, 250, center_y)
        painter.drawLine(80, 80, 220, 220)
        painter.drawLine(80, 220, 220, 80)
        
        # Draw polygon
        painter.setPen(QColor(0, 150, 255))
        painter.setBrush(QColor(0, 150, 255, 100))
        
        # Placeholder values for different brain waves
        values = {
            "Delta": 100,
            "Theta": 150,
            "Alpha": 180,
            "Beta": 200,
            "Gamma": 120
        }
        
        points = []
        angle_step = 2 * math.pi / len(values)
        
        for i, (key, value) in enumerate(values.items()):
            angle = i * angle_step - math.pi / 2 # start from top
            x = center_x + value * math.cos(angle)
            y = center_y + value * math.sin(angle)
            # Konversi x dan y menjadi integer sebelum membuat QPoint
            points.append(QPoint(int(x), int(y)))
            
            # Label
            label_x = center_x + (value + 20) * math.cos(angle)
            label_y = center_y + (value + 20) * math.sin(angle)
            painter.drawText(int(label_x), int(label_y), key)
            
        painter.drawPolygon(QPolygon(points))
        painter.end()

        radar_label = QLabel()
        radar_label.setPixmap(radar_diagram)
        radar_layout.addWidget(radar_label)
        
        return radar_widget

    def _create_riwayat_rekaman_page(self):
        self.riwayat_rekaman_page = QWidget()
        self.riwayat_rekaman_page.setObjectName("ContentFrame")
        layout = QVBoxLayout(self.riwayat_rekaman_page)
        layout.setAlignment(Qt.AlignCenter)
        self.riwayat_rekaman_title = QLabel("Halaman Riwayat Rekaman")
        self.riwayat_rekaman_title.setStyleSheet("background-color: transparent;")
        self.riwayat_rekaman_info = QLabel("Lihat riwayat rekaman EEG di sini.")
        self.riwayat_rekaman_info.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.riwayat_rekaman_title)
        layout.addWidget(self.riwayat_rekaman_info)
        self.stacked_widget.addWidget(self.riwayat_rekaman_page)

    def _update_responsive_fonts(self):
        """Menyesuaikan ukuran font secara dinamis berdasarkan ukuran jendela."""
        width = self.width()
        height = self.height()
        base_size = min(width, height) / 40 # Calculate a base size based on window dimensions
        
        # Header and main titles
        font_header = QFont("Helvetica", max(16, int(base_size * 0.9)), QFont.Bold)
        self.header_label.setFont(font_header)
        
        font_title = QFont("Helvetica", max(18, int(base_size * 0.9)), QFont.Bold)
        self.form_title.setFont(font_title)
        self.preview_title.setFont(font_title)
        
        # To avoid AttributeError on the new Rekaman Baru page, we need to check if the widgets exist.
        if hasattr(self, 'rekaman_baru_title'):
            self.rekaman_baru_title.setFont(font_title)
        if hasattr(self, 'riwayat_rekaman_title'):
            self.riwayat_rekaman_title.setFont(font_title)
        
        # Sidebar labels and buttons
        font_sidebar_title = QFont("Helvetica", max(14, int(base_size * 0.)), QFont.Bold)
        self.features_label.setFont(font_sidebar_title)
        
        # Update stylesheet for sidebar buttons to use new font size
        self.setStyleSheet(self.styleSheet() + f"""
            .SidebarButton {{
                font-size: {max(16, int(base_size * 0.8))}pt;
            }}
        """)
        
        # Form labels
        font_form_label = QFont("Helvetica", max(14, int(base_size * 0.7)))
        for label in self.form_labels.values():
            label.setFont(font_form_label)

        # Main content and info labels
        font_info = QFont("Helvetica", max(9, int(base_size * 0.45)))
        self.info_label.setFont(font_info)
        
        font_page_info = QFont("Helvetica", max(10, int(base_size * 0.5)))
        
        # Update fonts on the new page
        if hasattr(self, 'rekaman_baru_page'):
            for widget in self.rekaman_baru_page.findChildren(QLabel):
                widget.setFont(font_page_info)
            for widget in self.rekaman_baru_page.findChildren(QPushButton):
                widget.setFont(font_page_info)
            for widget in self.findChildren(QRadioButton):
                widget.setFont(font_form_label)

            # You can add more widget types here if needed

        if hasattr(self, 'riwayat_rekaman_info'):
            self.riwayat_rekaman_info.setFont(font_page_info)

        # Update preview page fonts responsively
        font_preview_label = QFont("Helvetica", max(10, int(base_size * 0.6)), QFont.Bold)
        font_preview_value = QFont("Helvetica", max(10, int(base_size * 0.6)))

        for label, value_label in self.preview_labels.values():
            label.setFont(font_preview_label)
            value_label.setFont(font_preview_value)

            
    def resizeEvent(self, event):
        """Dipanggil setiap kali ukuran jendela diubah."""
        self._update_responsive_fonts()
        super().resizeEvent(event)
        
    def show_data_subjek_form(self):
        for entry in self.entries.values():
            entry.clear()
        self.stacked_widget.setCurrentWidget(self.data_subjek_form_page)
        print("Menampilkan Data Subjek Form")

    def add_data(self):
        data = {label: entry.text().strip() for label, entry in self.entries.items()}

        # Ambil jenis kelamin
        if self.laki_radio.isChecked():
            data["Jenis Kelamin"] = "Laki-laki"
        elif self.perempuan_radio.isChecked():
            data["Jenis Kelamin"] = "Perempuan"
        else:
            data["Jenis Kelamin"] = ""

        if not all(data.values()):
            QMessageBox.warning(self, "Peringatan", "Semua kolom harus diisi dan pilih jenis kelamin!")
            return

        self.current_preview_data = data
        QMessageBox.information(self, "Sukses", "Data subjek berhasil ditambahkan! Silakan cek halaman 'Pratinjau Data'.")
        
        for entry in self.entries.values():
            entry.clear()
            self.laki_radio.setChecked(False)
            self.perempuan_radio.setChecked(False)

        self.show_data_preview()

    def show_data_preview(self):
        for i in reversed(range(self.preview_grid_layout.count())):
            widget = self.preview_grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
            else:
                layout_item = self.preview_grid_layout.itemAt(i)
                if layout_item.layout():
                    for j in reversed(range(layout_item.layout().count())):
                        child_widget = layout_item.layout().itemAt(j).widget()
                        if child_widget:
                            child_widget.setParent(None)
                    layout_item.layout().setParent(None)

        if not self.current_preview_data:
            no_data_label = QLabel("Tidak ada data subjek untuk ditampilkan.")
            no_data_label.setFont(QFont("Helvetica", 14))
            no_data_label.setAlignment(Qt.AlignCenter)
            no_data_label.setStyleSheet("background-color: transparent;")
            self.preview_grid_layout.addWidget(no_data_label)
        else:
            self.preview_labels = {} # Clear the dictionary for new data
            for label_text, value in self.current_preview_data.items():
                row_layout = QHBoxLayout()
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(10)

                label = QLabel(f"{label_text}:")
                label.setFont(QFont("Helvetica", 10, QFont.Bold))
                label.setStyleSheet("background-color: transparent;")
                label.setFixedWidth(150)
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                row_layout.addWidget(label)

                value_label = QLabel(value)
                value_label.setFont(QFont("Helvetica", 10))
                value_label.setStyleSheet("background-color: transparent;")
                value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                row_layout.addWidget(value_label, 1)
                
                self.preview_grid_layout.addLayout(row_layout)
                self.preview_grid_layout.addSpacing(5)
                
                # Simpan referensi ke kedua label dalam sebuah tuple
                self.preview_labels[label_text] = (label, value_label)

        self.stacked_widget.setCurrentWidget(self.data_preview_page)
        print("Menampilkan Pratinjau Data Subjek")

    def show_rekaman_baru(self):
        self.stacked_widget.setCurrentWidget(self.rekaman_baru_page)
        print("Menampilkan Rekaman Baru")

    def show_riwayat_rekaman(self):
        self.stacked_widget.setCurrentWidget(self.riwayat_rekaman_page)
        print("Menampilkan Riwayat Rekaman")

    def save_as_pdf(self):
        if not self.current_preview_data:
            QMessageBox.warning(self, "Peringatan", "Tidak ada data untuk disimpan sebagai PDF.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Simpan Data Subjek sebagai PDF", "", "PDF files (*.pdf)")
        if not file_name:
            return

        c = canvas.Canvas(file_name, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2.0, height - 70, "Data Subjek Pasien")

        c.setFont("Helvetica", 14)
        y_position = height - 150
        line_height = 20

        for label, value in self.current_preview_data.items():
            c.drawString(70, y_position, f"{label}:")
            c.drawString(250, y_position, value)
            y_position -= line_height

        c.showPage()
        c.save()
        QMessageBox.information(self, "Sukses", f"Data berhasil disimpan sebagai PDF:\n{file_name}")

    def save_as_png(self):
        if not self.current_preview_data:
            QMessageBox.warning(self, "Peringatan", "Tidak ada data untuk disimpan sebagai PNG.")
            return

        file_name, _ = QFileDialog.getSaveFileName(self, "Simpan Data Subjek sebagai PNG", "", "PNG files (*.png)")
        if not file_name:
            return

        temp_preview_widget = QWidget()
        temp_preview_widget.setStyleSheet("background-color: white;")
        temp_preview_layout = QVBoxLayout(temp_preview_widget)
        temp_preview_layout.setContentsMargins(50, 50, 50, 50)

        temp_title = QLabel("Data Subjek Pasien")
        temp_title.setFont(QFont("Helvetica", 20, QFont.Bold))
        temp_title.setAlignment(Qt.AlignCenter)
        temp_title.setStyleSheet("background-color: transparent;")
        temp_preview_layout.addWidget(temp_title)
        temp_preview_layout.addSpacing(30)

        temp_data_layout = QVBoxLayout()
        for label_text, value in self.current_preview_data.items():
            row_layout = QHBoxLayout()
            label = QLabel(f"{label_text}:")
            label.setFont(QFont("Helvetica", 12, QFont.Bold))
            label.setFixedWidth(120)
            label.setStyleSheet("background-color: transparent;")
            row_layout.addWidget(label)

            value_label = QLabel(value)
            value_label.setFont(QFont("Helvetica", 12))
            value_label.setStyleSheet("background-color: transparent;")
            row_layout.addWidget(value_label, 1)
            temp_data_layout.addLayout(row_layout)
            temp_data_layout.addSpacing(5)

        temp_preview_layout.addLayout(temp_data_layout)
        temp_preview_layout.addStretch()

        temp_preview_widget.setFixedSize(600, 750)

        pixmap = temp_preview_widget.grab()
        
        if not pixmap.isNull():
            pixmap.save(file_name, "PNG")
            QMessageBox.information(self, "Sukses", f"Data berhasil disimpan sebagai PNG:\n{file_name}")
        else:
            QMessageBox.critical(self, "Error", "Gagal menangkap tampilan sebagai PNG.")

        temp_preview_widget.deleteLater()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EEGMonitorApp()
    window.show()
    sys.exit(app.exec_())
